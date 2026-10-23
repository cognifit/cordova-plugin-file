/*
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 */

// MIME type lookup for the local filesystem.
#import <Foundation/Foundation.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#if __IPHONE_OS_VERSION_MIN_REQUIRED < 140000
#import <MobileCoreServices/MobileCoreServices.h>
#endif

static inline NSString *CDVFileTypeIdentifierForExtension(NSString *extension)
{
    if (@available(iOS 14.0, macOS 11.0, *)) {
        return [UTType typeWithTag:extension tagClass:UTTagClassFilenameExtension conformingToType:nil].identifier;
    }
#if __IPHONE_OS_VERSION_MIN_REQUIRED < 140000
    // Compatibility with iOS 11-13; these APIs are only deprecated from iOS 15.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    return CFBridgingRelease(UTTypeCreatePreferredIdentifierForTag(kUTTagClassFilenameExtension, (__bridge CFStringRef)extension, NULL));
#pragma clang diagnostic pop
#else
    return nil;
#endif
}

static inline NSString *CDVFileMIMETypeForIdentifier(NSString *identifier)
{
    if (!identifier) {
        return nil;
    }
    if (@available(iOS 14.0, macOS 11.0, *)) {
        return [UTType typeWithIdentifier:identifier].preferredMIMEType;
    }
#if __IPHONE_OS_VERSION_MIN_REQUIRED < 140000
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    return CFBridgingRelease(UTTypeCopyPreferredTagWithClass((__bridge CFStringRef)identifier, kUTTagClassMIMEType));
#pragma clang diagnostic pop
#else
    return nil;
#endif
}
