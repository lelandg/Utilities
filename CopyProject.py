#!/usr/bin/env python
# coding=utf-8
"""
@version: 1.0.0
@author: Leland Green... <aboogieman@gamil.com>
@copyright: Copyright (c) 2012 Singularity Mage
All Rights Reserved

Released under the MIT license. You may use this script for any purpose, including
commercial, as long as the copyright and license information remains intact.

A copy of the MIT license is not included. If you don't know what that is, please
look it up. (It seems silly to include a license that's longer than all of the code!)

Run with no parameters to see usage screen. See comments below for details.

This is intended to copy a VS project from one dir to another. I have some code
below for XCode projects, but it is untested, but may work. I'd like feedback on
this and may be able to make it work.

By default, relative paths are replaced with absolute paths, so anything in a
project *should* still work. There is an option to disable this. If disabled,
you should run with output to the same relative level as source, or else have
a copy of all required files in the destination tree.

Note that this reads one "line" at a time, including binary files. That has a
potential to run out of memory, or cause other problems. So far, this has worked
well in my limited tests. If you hit problems, add the file extension (or ending
string) to NoPathReplaceFileTypes.
"""
__version__ = __doc__.split("@version:")[1].split("\n")[0].strip()
__copyright__ =  __doc__.split("@copyright:")[1].split("\n")[0].strip()
__author__ = __doc__.split("@copyright:")[1].split("\n")[0].strip()

import sys
import os
#import shutil
import re

# Will exclude any directories that *begin with* these strings. (Case insensitive.)
ExcludeDirsWith = ["_Resharper", "Intermediate", "Output", "_UpgradeReport_Files", "ipch"]
# E.g., "<ProjectDir>Output" will be excluded, but "<ProjectDir>GUI/Output" will not.

# Do not do path replacement in files ending with:
NoPathReplaceFileTypes = [".PNG", ".TGA", ".DAE"]

RemoveProjectDir = True # When true, will remove "$(ProjectDir)\" from all paths before checking.
                        # Only applies when fixrelative is used.

# Note that the ';' is not really invalid, but I'm including it so that in " ../..;" the
# "../.." portion will be replaced. Otherwise only the "../" would be. This is because of my
# regex below. If you don't like it, please submit a patch. :)
invalidWindowsChars = "\x22\x3C\x3E\x7C\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F"\
                      "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x3A\x2A\x3F\x5C\x2F;"
invalidCharsLinux = "/"

if sys.platform == 'win32':
    invalidChars = invalidWindowsChars
elif sys.platform == 'linux2' or sys.platform == 'darwin':
    # I'm not sure what the requirements are for projects on other platforms
    #invalidChars = invalidCharsLinux
    invalidChars = invalidWindowsChars
else:
    #invalidChars = invalidCharsLinux
    invalidChars = invalidWindowsChars

reRelPath = re.compile(r"((\.{2}[\\/]{1,2}\.{2}[\\/]*)[^" + invalidChars + "]*)")
reDots = re.compile(r"(?=\.{2}[\\/])")

def relativeToAbsolutePath(sourceString, sourcePath = ''):
    """
    sourceString is any string that may include a relative path as part of it.
    The path will be matched up to ' or " chars, or end of line.

    sourcePath is the path that will be used as the "starting point" to calculate
    the absolute path. If not provided, current dir will be used. Note that this is
    where you're *running* the script from, not where the script *is*.

    """
    if RemoveProjectDir and sourceString.find("$(ProjectDir)\\") >= 0:
        sourceString = sourceString.replace("$(ProjectDir)\\", "")

    match = reRelPath.search(sourceString)
    if not match:
        return sourceString

    if sourcePath == '':
        sourcePath = os.getcwd()
    pathPart = match.group()
    if os.path.isabs(pathPart):
        return sourceString

    absPath = sourcePath

    #noinspection PyBroadException
    try:
        joinedPath = os.path.join(sourcePath, pathPart).replace('\\\\','\\')
        # This can raise an exception if the string isn't really a path (as VS2010 stores).
        absPath = os.path.abspath(joinedPath)
    except:
        pass

    return sourceString.replace(pathPart, absPath)


def newProject(sourcePath, targetPath, options):

    sourcePathLen = len(sourcePath)
    if sourcePath[-1] != os.path.sep:
        sourcePath += os.path.sep
        sourcePathLen += 1

    sourceProjectName = os.path.split(sourcePath[:-1])[1]
    if sourceProjectName == "":
        raise Exception("Source path should not be root path.")

    if targetPath[-1] == os.path.sep:
        targetPath = targetPath[:-1]
    tagetDir, targetProjectName = os.path.split(targetPath)
    if targetProjectName == "":
        raise Exception("Target path should not be root path.")

    for root, dirs, files in os.walk(sourcePath):
        skip = False
        for exclude in ExcludeDirsWith:
            if root[sourcePathLen:].upper().startswith(exclude.upper()):
                skip = True
        if skip:
            continue

        for fname in files:
            destDir = os.path.join(targetPath, root[sourcePathLen:])
            if not os.path.exists(destDir):
                os.makedirs(destDir)
            sourceFileName = os.path.join(root, fname)
            destFileName = os.path.join(destDir, fname)
            if fname.find(sourceProjectName) >= 0:
                destFileName = destFileName.replace(sourceProjectName, targetProjectName)

            if os.path.exists(destFileName):
                raise Exception("File '%s' already exists. Remove if you really mean it! :)" % destFileName)

            base, ext = os.path.splitext(fname)

            #if base.upper() == sourceProjectName.upper() and ext.upper() in [".SLN", ".VCPROJ"]:
                # We have a project file, do search/replace

            # I'm playing it safe and replacing every occurence of both the project name and directory.
            # That way, if you have a "ProjectName.h", it will still be included in the .cpp, etc.
            # This could (in theory) cause problems for some binary files, e.g., if something is stored
            # as a Pascal string. If you hit errors, add those file types to NoPathReplaceFileTypes
            # at the top of the script.
            inf = file(sourceFileName, "rb")
            outf = file(destFileName, "wb")
            for line in inf:
                line = line.replace(sourceProjectName, targetProjectName)\
                        .replace(sourcePath, targetPath)
                if line.find(sourceProjectName.upper()):
                    line = line.replace(sourceProjectName.upper(), targetProjectName.upper())
                if options.fixrelative:
                    replace = True
                    for ext in NoPathReplaceFileTypes:
                        if sourceFileName.upper().endswith(ext.upper()):
                            replace = False
                    if replace:
                        line = relativeToAbsolutePath(line, root)
                outf.write(line)


def main(argc=len(sys.argv), argv=sys.argv):
    from optparse import OptionParser
    sourcePath = os.getcwd()
    parser = OptionParser(usage="\r\n       %prog [options] [SourcePath] <TargetPath>\r\n"
    "Where:\r\n\r\n"
    "[SourcePath] is the source project *directory*.\r\n"
    "<TargetPath> is the target directory you want to create. If this does not \r\n"
    "             contain a directory, a folder will be created in the current\r\n"
    "             directory.",
    version= "\r\n%prog " + __version__)

    parser.add_option("-r", "--fixrelative", dest="fixrelative", default=True,
                action="store_false", help="Do not update relative paths to absolute. "\
                "Default = do.")

    (options, args) = parser.parse_args(argv[1:])
    if len(args) < 2:
        parser.print_help()
        sys.exit()

    if len(args) > 1:
        sourcePath = args[0]
        targetPath = args[1]
    else:
        targetPath = args[0]

    newProject(sourcePath, targetPath, options)

if __name__ == "__main__":
    main()
