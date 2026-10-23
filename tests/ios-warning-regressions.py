#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements. See the NOTICE file for additional
# information regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run Foundation/UTType regressions on macOS without changing a Cordova app.

The harness compiles the methods extracted from the actual plugin sources.
It covers their platform-independent behavior, not device file access.
Run: python3 tests/ios-warning-regressions.py
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

# The removed filesystem must not be installed or registered by the plugin.
import xml.etree.ElementTree as ET
plugin = ET.parse(ROOT / 'plugin.xml').getroot()
for node in plugin.iter():
    assert 'AssetsLibrary' not in node.attrib.get('src', ''), node.attrib
assert 'CDVAssetLibraryFilesystem' not in (ROOT / 'src/ios/CDVFile.m').read_text()


def method(filename, signature):
    source = (ROOT / 'src/ios' / filename).read_text()
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


harness = r'''
#import <Foundation/Foundation.h>
#import "CDVFileType.h"
#import <CoreServices/CoreServices.h>

NSString * const kCDVFilesystemURLPrefix = @"cdvfile";
__URL_INTERFACE__
__URL_IMPLEMENTATION__

@interface Encoding : NSObject
- (NSString *)encodePath:(NSString *)path;
@end
@implementation Encoding
ENCODING_METHOD
@end

@interface LocalMIME : NSObject
@property (nonatomic, copy) NSString *name;
- (CDVFilesystemURL *)URLforFullPath:(NSString *)path;
+ (NSString *)getMimeTypeFromPath:(NSString *)path;
- (NSString *)mimeTypeForFileAtPath:(NSString *)path;
@end
@implementation LocalMIME
__LOCAL_URL_METHOD__
__MIME_LOOKUP__
__FILE_MIME_LOOKUP__
@end

static void equal(NSString *actual, NSString *expected) {
    if (!((!actual && !expected) || [actual isEqualToString:expected])) {
        NSLog(@"Expected %@; got %@", expected, actual);
        exit(1);
    }
}

int main(void) { @autoreleasepool {
    Encoding *encoder = [Encoding new];
    equal([encoder encodePath:@"cdvfile://localhost/persistent/a b.txt"],
          @"cdvfile://localhost/persistent/a%20b.txt");
    equal([encoder encodePath:@"file:///tmp/a%20b.txt"], @"file:///tmp/a%20b.txt");
    equal([encoder encodePath:@"file:///tmp/ñ#%.txt"], nil); // malformed percent input
    equal([encoder encodePath:@"file:///tmp/%C3%B1%23%25.txt"], @"file:///tmp/%C3%B1%23%25.txt");
    equal([encoder encodePath:@"cdvfile://localhost/persistent/photo.jpg?id=ABC&ext=JPG"],
          @"cdvfile://localhost/persistent/photo.jpg?id=ABC&ext=JPG");
    CDVFilesystemURL *legacy = [CDVFilesystemURL fileSystemURLWithString:
        @"assets-library://asset/asset.JPG?id=ABC&ext=JPG"];
    equal(legacy.fileSystemName, nil);
    equal(legacy.fullPath, nil);
    equal([encoder encodePath:nil], nil);

    LocalMIME *local = [LocalMIME new];
    local.name = @"persistent";
    for (NSString *path in @[@"/a b.txt", @"/ñ#%.txt", @"/photo?name.jpg", @"/folder/a:b.txt"]) {
        CDVFilesystemURL *url = [local URLforFullPath:path];
        equal(url.fileSystemName, @"persistent");
        equal(url.fullPath, path);
    }
    equal([local URLforFullPath:@"relative.txt"].fullPath, @"/relative.txt");
    if ([local URLforFullPath:nil] != nil) return 1;

    // Check the legacy whole-URI contract across printable ASCII characters.
    // The deprecated API is deliberately used only as a regression oracle.
    for (int c = 32; c < 127; c++) {
        if (c == '%') continue;
        NSString *uri = [NSString stringWithFormat:@"cdvfile://localhost/persistent/a%cb", c];
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
        NSString *expected = [uri stringByAddingPercentEscapesUsingEncoding:NSUTF8StringEncoding];
#pragma clang diagnostic pop
        equal([encoder encodePath:uri], expected);
    }
    equal([LocalMIME getMimeTypeFromPath:nil], nil);
    equal([LocalMIME getMimeTypeFromPath:@"example.txt"], @"text/plain");
    equal([LocalMIME getMimeTypeFromPath:@"example.png"], @"image/png");
    equal([LocalMIME getMimeTypeFromPath:@"example.jpg"], @"image/jpeg");
    equal([LocalMIME getMimeTypeFromPath:@"example.css"], @"text/css");
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    CFStringRef legacyType = UTTypeCreatePreferredIdentifierForTag(kUTTagClassFilenameExtension, CFSTR("m4a"), NULL);
    NSString *legacyMIME = CFBridgingRelease(UTTypeCopyPreferredTagWithClass(legacyType, kUTTagClassMIMEType));
    CFRelease(legacyType);
#pragma clang diagnostic pop
    equal([LocalMIME getMimeTypeFromPath:@"example.m4a"], legacyMIME ?: @"audio/mp4");
    equal([LocalMIME getMimeTypeFromPath:@"example.cdv_unknown_extension"], nil);
    equal(CDVFileMIMETypeForIdentifier(nil), nil);
    equal(CDVFileMIMETypeForIdentifier(@"public.jpeg"), @"image/jpeg");

    NSString *dir = NSProcessInfo.processInfo.environment[@"CDV_TEST_DIRECTORY"];
    NSString *unknown = [dir stringByAppendingPathComponent:@"unknown.cdv_unknown_extension"];
    NSString *text = [dir stringByAppendingPathComponent:@"known.txt"];
    [[NSData data] writeToFile:unknown atomically:YES];
    [[NSData data] writeToFile:text atomically:YES];
    LocalMIME *fs = [LocalMIME new];
    equal([fs mimeTypeForFileAtPath:unknown], @"application/octet-stream");
    equal([fs mimeTypeForFileAtPath:text], @"text/plain");
    equal([fs mimeTypeForFileAtPath:[dir stringByAppendingPathComponent:@"missing"]], nil);
    puts("PASS: URI encoding, rejected legacy photo URLs, MIME lookup and unknown/missing files");
} return 0; }
'''
for token, filename, marker in [
        ('__URL_INTERFACE__', 'CDVFile.h', '@interface CDVFilesystemURL :'),
        ('__URL_IMPLEMENTATION__', 'CDVFile.m', '@implementation CDVFilesystemURL')]:
    source = (ROOT / 'src/ios' / filename).read_text()
    start = source.index(marker)
    end = source.index('@end', start) + len('@end')
    harness = harness.replace(token, source[start:end])
harness = harness.replace('__LOCAL_URL_METHOD__', method('CDVLocalFilesystem.m', '- (CDVFilesystemURL *)URLforFullPath:'))
harness = harness.replace('ENCODING_METHOD', method('CDVFile.m', '-(NSString *)encodePath:'))
harness = harness.replace('__MIME_LOOKUP__', method('CDVLocalFilesystem.m', '+ (NSString*)getMimeTypeFromPath:'))
harness = harness.replace('__FILE_MIME_LOOKUP__', method('CDVLocalFilesystem.m', '- (NSString*) mimeTypeForFileAtPath:'))

with tempfile.TemporaryDirectory(prefix='cordova-file-tests-') as directory:
    directory = Path(directory)
    source = directory / 'regressions.m'
    binary = directory / 'regressions'
    source.write_text(harness)
    subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-Werror',
                    '-D__IPHONE_OS_VERSION_MIN_REQUIRED=170000',
                    '-I', str(ROOT / 'src/ios'), '-framework', 'Foundation',
                    '-framework', 'UniformTypeIdentifiers', '-framework', 'CoreServices', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, env={**os.environ, 'CDV_TEST_DIRECTORY': str(directory)})
