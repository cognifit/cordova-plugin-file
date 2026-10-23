#!/bin/sh
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
set -eu
: "${CORDOVA_HEADERS:?Set CORDOVA_HEADERS to CordovaLib/include from cordova-ios}"
plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
objects=$(mktemp -d)
trap 'rm -rf "$objects"' EXIT HUP INT TERM
for target in 11.0 17.0 26.0; do
    for source in CDVFile CDVLocalFilesystem; do
        xcrun --sdk iphonesimulator clang -c -fobjc-arc -fblocks -Werror \
            -Wunguarded-availability-new -target "arm64-apple-ios${target}-simulator" \
            -isysroot "$(xcrun --sdk iphonesimulator --show-sdk-path)" \
            -isystem "$CORDOVA_HEADERS" "$plugin_root/src/ios/$source.m" \
            -o "$objects/$source-$target.o"
    done
    echo "PASS: iOS $target simulator compilation with warnings as errors"
done
