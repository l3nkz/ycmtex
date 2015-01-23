#!/usr/bin/env python2
#
# TexCompleter - Semantic completer for YouCompleteMe which handles Tex files.
# Copyright (C) 2015 Till Smejkal <till.smejkal@ossmail.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

###
# Standard library imports.
###
from __future__ import print_function

from os.path import dirname, join, isfile, isdir, splitext
from os import listdir

from functools import total_ordering

import logging

###
# YCMD imports.
###
from ycmd.completers.completer import Completer
from ycmd.responses import BuildCompletionData
from ycmd.utils import AddNearestThirdPartyFoldersToSysPath

###
# Third Party imports.
###
# First add the local 'third_party' folder to the package search path.
AddNearestThirdPartyFoldersToSysPath(__file__)
import bibtexparser


logger = logging.getLogger(__name__)

class TexObject:

    def _smart_shorten(self, to_shorten, length, delta = 5):
        """
        Shorten a given string to the given length but on a smart way.

        The specified length is not necessary the one which the string will have
        after the shortening process. This is because of the way the method is
        working. It tries to shorten the string at word boundaries if possible.
        Hence the string can be a bit longer or shorter than specified.

        :param to_shorten: The string which should be shortened.
        :type to_shorten: str
        :param length: The length to which the string should be shortened.
        :type length: int
        :param delta: The allowed delta which the string is allowed to be longer
                      or shorter. (Defaults to 5)
        :type delta: int
        :rtype: str
        :return: The smartly shortened string.
        """
        # As ' ...' is added to the end of the shortened string a little bit
        # more space is needed.
        goal_length = length - 4

        if len(to_shorten) >= goal_length + delta:
            # Find the boundaries of the word which gets shortened.
            next_space = to_shorten.find(" ", length)
            prev_space = to_shorten.rfind(" ", 0, length)

            if next_space != -1 and next_space < goal_length + delta:
                # 1. Try to keep the word in the result.
                return to_shorten[:next_space] + " ..."
            elif prev_space != -1 and prev_space > goal_length - delta:
                # 2. Remove the whole word from the result.
                return to_shorten[:prev_space] + " ..."
            else:
                # The word is to large to remove it completely. So it must be
                # split.
                return to_shorten[:goal_length - 1] + ". ..."
        else:
            return to_shorten

    def completion(self):
        """
        The completion text which should be presented to the user of the
        completer.

        This method must be implemented by every TeX object which the completer
        supports.

        :rtype: str
        :return: The completion text of this object.
        """
        raise NotImplementedError()

    def extra_info(self, shortened = True):
        """
        The additional information for the completion which should be presented
        to the user of the completer.

        This method must be implemented by every TeX object which the completer
        supports.

        :param shortened: Whether or not the information text should be
                          shortened or not. (Defaults to True)
        :type shortened: bool
        :rtype: str
        :return: The additional information of this object.
        """
        raise NotImplementedError()


@total_ordering
class TexReferable(TexObject):

    MaxNameLength = 50

    AbbreviationMap = {
            "unknown" : "u",
            "chapter" : "C",
            "section" : "S",
            "subsection" : "s",
            "subsubsection" : "U",
            "paragraph" : "P",
            "subparagraph" : "p",
            "figure" : "F",
            "table" : "T",
            "lstlisting" : "L"
    }

    def __init__(self, label, name="Unknown", ref_type="unknown"):
        """
        Constructor

        :param label: The identifier which is used to reference it in the text.
        :type label: str
        :param name: The actual name of the referable object.
        :type name: str
        :param ref_type: The type of the referable object.
        :type ref_type: str
        """
        self._label = label
        self._name = name
        self._short_name = None
        self._ref_type = ref_type
        self._abbreviation = self.AbbreviationMap[ref_type] if \
                self.AbbreviationMap.has_key(ref_type) else \
                self.AbbreviationMap["unknown"]

    def __eq__(self, other):
        """
        Compare for equality with another referable object.

        Equality is reached if all three parameters (label, name, and ref_type)
        are equal.

        :param other: The object which should be tested for equality.
        :type other: TexReferable
        :rtype: bool
        :return: Whether or not the objects are equal.
        """
        if not isinstance(other, TexReferable):
            return ValueError("Equality can only be tested for objects with" +
                    "the same type")

        return self._label == other._label and self._name == other._name and \
                self._ref_type == other._ref_type

    def __lt__(self, other):
        """
        Determine if the current object is less than the other one.

        The current object is less than the other one if the label is less, or
        if the name is less, or if the ref_type is less than the one of the
        other object.

        :param other: The object which should be tested against.
        :type other: TexReferable
        :rtype: bool
        :return: Whether or not the current object is less then the other one.
        """
        if not isinstance(other, TexReferable):
            raise ValueError("Less than can only be tested for objects with" +
                    "the same type.")

        if self._label != other._label:
            return self._label < other._label
        elif self._name != other._name:
            return self._name < other._name
        elif self._ref_type != other._ref_type:
            return self._ref_type < other._ref_type
        else:
            return False

    def shorten(self, ignore_name = "Unknown"):
        """
        Shorten the name of the referable object so that it is not too long.

        This method just alters the internal state of the object.

        :param ignore_name: If the name is equal to the given one, shorten is
                            skipped for the name. (Defaults to 'Unknown')
        :type ignore_name: str
        :rtype: TexReferable
        :return: The current object
        """
        # Smartly shorten the name of the referable object if this name should
        # not be ignored.
        if self._name != ignore_name:
            self._short_name = self._smart_shorten(self._name, self.MaxNameLength)

        return self

    def completion(self):
        """
        :see TexObject.completion:
        """
        return self._label

    def extra_info(self, shorten = True):
        """
        :see TexObject.completion:
        """
        if shorten:
            if self._short_name is None:
                name = self.shorten()._short_name
            else:
                name = self._short_name
        else:
            name = self._name

        return self._abbreviation + " " + name


@total_ordering
class TexCitable(TexObject):

    MaxTitleLength = 45

    AbbreviationMap = {
            "unknown" : "u",
            "article" : "A",
            "book" : "B",
            "booklet" : "b",
            "conference" : "C",
            "inbook" : "I",
            "incollection" : "i",
            "inproceedings" : "p",
            "journal" : "J",
            "manual" : "M",
            "masterthesis" : "t",
            "misc" : "m",
            "phdthesis" : "T",
            "proceedings" : "P",
            "techreport" : "R",
            "unpublished" : "U"
    }

    def __init__(self, label, title="Unknown", author="Unknown",
            cite_type="unknown"):
        """
        Constructor

        :param label: The identifier which is used to cite it in the text.
        :type label: str
        :param title: The title of the cited object. (Defaults to 'Unknown')
        :type title: str
        :param author: The author of the cited object. (Defaults to 'Unknown')
        :type author: str
        :param cite_type: The Bibtex type of the cited object (Defaults to
                          'Unknown')
        :type cite_type: str
        """
        self._label = label
        self._title = title
        self._short_title = None
        self._author = author
        self._short_author = None
        self._cite_type = cite_type
        self._abbreviation = self.AbbreviationMap[cite_type] if \
                self.AbbreviationMap.has_key(cite_type) else \
                self.AbbreviationMap["unknown"]

    def __eq__(self, other):
        """
        Compare for equality with another citable object.

        Equality is reached if all parameters (label, title, author, and cite_type)
        are equal.

        :param other: The object which should be tested for equality.
        :type other: TexCitable
        :rtype: bool
        :return: Whether or not the objects are equal.
        """
        if not isinstance(other, TexCitable):
            return ValueError("Equality can only be tested for objects with" +
                    "the same type")

        return self._label == other._label and self._title == other._title and \
                self._author == other._author and self._cite_type == other._cite_type

    def __lt__(self, other):
        """
        Determine if the current object is less than the other one.

        The current object is less than the other one if it label is less, or if
        the title is less, or if the author is less, or if the cite_type is less
        than the one of the other object.

        :param other: The object which should be tested against.
        :type other: TexCitable
        :rtype: bool
        :return: Whether or not the current object is less then the other one.
        """
        if not isinstance(other, TexCitable):
            raise ValueError("Less than can only be tested for objects with" +
                    "the same type.")

        if self._label != other._label:
            return self._label < other._label
        elif self._title != other._title:
            return self._title < other._title
        elif self._author != other._author:
            return self._author < other._author
        elif self._cite_type != other._cite_type:
            return self._cite_type < other._cite_type
        else:
            return False

    def shorten(self, ignore_title = "Unknown", ignore_author = "Unknown"):
        """
        Shorten the title and the author string of the citable object so that
        they can be displayed properly.

        This method just alters the internal state of the object.

        :param ignore_title: If the title is equal to the given one, shorten is
                             skipped for the title. (Defaults to 'Unknown')
        :type ignore_title: str
        :param ignore_author: If the author is equal to the given one, shorten
                              is skipped for the author. (Defaults to 'Unknown')
        :type ignore_author: str
        :rtype: TexCitable
        :return: The current object
        """
        # Smartly shorten the title if it should not be ignored.
        if self._title != ignore_title:
            self._short_title = self._smart_shorten(self._title, self.MaxTitleLength)

        # Shorten the authors if they should not be ignored.
        if self._author != ignore_author:
            # If the author string contains multiple authors replace them with
            # 'et. al.'.
            if " and " in self._author:
                # There are multiple authors mentioned. Replace them by 'et. al.'.
                # And remember where the first author ended.
                end_of_first_author = self._author.find(" and ")
                self._short_author = self._author[:end_of_first_author].strip() + " et. al."
            else:
                # There is just one author. So set the variable to the end of the
                # string.
                end_of_first_author = len(self._author)
                self._short_author = self._author

            # Just keep the authors surname and not the first and middle names.
            # If they are separated by a "," otherwise keep the full name.
            if "," in self._author[:end_of_first_author]:
                end_of_surname = self._author[:end_of_first_author].find(",")

                # Build the resulting name.
                self._short_author = self._short_author[:end_of_surname].strip() + \
                        self._short_author[end_of_first_author:]

        return self

    def completion(self):
        """
        :see TexObject.completion:
        """
        return self._label

    def extra_info(self, shorten = True):
        """
        :see TexObject.extra_info:
        """
        if shorten:
            if self._short_author is None or \
                    self._short_title is None:
                self.shorten()

            author = self._short_author
            title = self._short_title
        else:
            author = self._author
            title = self._title

        return self._abbreviation + " " + author + " - " + title


class TexCompleter(Completer):

    ###
    # List of Latex commands and options known by the completer.
    ###
    BibliographyCommands = ["bibliography"]
    ReferenceCommands = ["ref", "refv"]
    CitationCommands = ["cite", "citep", "citev"]
    SectioningCommands = ["chapter", "section", "subsection", "subsubsection",
            "paragraph", "subparagraph"]
    SpecialSectioningCommands = [("addchap", "chapter")]

    ###
    # List of supported VIM file types
    ###
    FileTypes = ["tex", "plaintex"]

    ###
    # Action which the completer supports
    ###
    class Actions(object):
        NoAction = 0
        Reference = 1
        Citation = 2

    def __init__(self, user_options):
        super(TexCompleter, self).__init__(user_options)

        self._action = self.Actions.NoAction

    def DebugInfo(self, request_data):
        file_name = request_data['filepath']

        return "TeX Completer for {}".format(file_name)

    def SupportedFiletypes(self):
        return self.FileTypes

    def ShouldUseNowInner(self, request_data):
        self._action = self.Actions.NoAction

        # Extract the last command
        current_line = request_data['line_value']
        word_start = request_data['start_column'] - 1

        # As according to the documentation the start_column points to the
        # begin of the word which is currently typed, the last command ends
        # at exactly this position.
        last_command = current_line[:word_start]

        if self._WantsReferable(last_command):
            self._action = self.Actions.Reference

            return True

        elif self._WantsCitable(last_command):
            self._action = self.Actions.Citation

            return True

        return False

    def ComputeCandidatesInner(self, request_data):
        if self._action == self.Actions.Citation:
            return self._CollectCitables(request_data)
        elif self._action == self.Actions.Reference:
            return self._CollectReferables(request_data)

        return []

    def _ExtractFromCommand(self, content, command_name, starable = False):
        """
        Extracts the argument of a LaTeX command.

        :param content: The string where the extraction should happen.
        :type content: str
        :param command_name: The name of the command from which the argument
                             should be extracted.
        :type command_name: str
        :param starable: Whether or not a stared version of the command exists,
                         too. (Defaults to False)
        :type starable: bool
        :rtype: str
        :return: The extracted command argument.
        """
        commands = ["\\"+command_name+"{"]

        if starable:
            commands.append("\\"+command_name+"*{")

        for command in commands:
            # Try to find the begin of the command in the given content.
            begin = content.find(command)

            # The command is not in the content. Try the next one.
            if begin == -1:
                continue

            # Determine the begin and the end of the commands argument.
            begin += len(command)
            end = content.find("}", begin)

            # Extract it and remove newlines.
            return content[begin:end].replace('\n', ' ').replace('\r', '')

        return None

    def _ExtractFromOption(self, content, option_name, compoundable = True):
        """
        Extracts the argument of an option of a command.

        :param content: The string where the extraction should happen.
        :type content: str
        :param option_name: The name of the option from which the argument
                            should be extracted.
        :type option_name: str
        :param compoundable: Whether or not the argument can be enclosed by
                             curly brackets. (Defaults to True)
        :type compoundable: bool
        :rtype: str
        :return: The extracted option argument.
        """
        option = option_name + "="

        # Try to find the begin of the option.
        begin = content.find(option)

        if begin == -1:
            # The option is not included in the given content string.
            return None

        begin += len(option)

        # Search for the end of the argument.
        if compoundable and content[begin] == "{":
            # The argument is surrounded by curly brackets. Extract it by
            # finding the corresponding closing one.
            begin += 1
            end = content.find("}", begin)
        else:
            # The argument is not surrounded by curly brackets, so search for
            # the possible end of the argument.
            end = begin

            while end < len(content) and \
                    (content[end] != " " and content[end] != "," and \
                    content[end] != "]" and content[end] != "}"):
                end += 1

        # Extract it and remove newlines.
        return content[begin:end].replace('\n', ' ').replace('\r', '')

    def _ExtractFromOptionOrCommand(self, content, name, starable = False,
            compoundable = True):
        """
        Extracts an argument from either an option or a command.

        :param content: The string where the extraction should happen.
        :type content: str
        :param name: The name of the option from which the argument should be
                     extracted.
        :type name: str
        :param starable: Whether or not a stared version of the command exists,
                         too. (Defaults to False)
        :type starable: bool
        :param compoundable: Whether or not the argument can be enclosed by
                             curly brackets. (Defaults to True)
        :type compoundable: bool
        :rtype: str
        :return: The extracted argument if possible.
        """
        # First try whether the given name is included as option in the given
        # content.
        extracted = self._ExtractFromOption(content, name, compoundable)

        if extracted is not None:
            return extracted

        # Next try if the given name is included as a command in the given
        # content.
        extracted = self._ExtractFromCommand(content, name, starable)

        if extracted is not None:
            return extracted

        # It was neither found is argument of a command nor of an option.
        return None

    def _WantsReferable(self, line):
        """
        This method checks if the line given ends with a LaTeX reference
        command.

        :param line: The line of text which should be checked.
        :type line: str
        :rtype: bool
        :return: Whether or not given line end with a LaTeX reference command.
        """
        for command in self.ReferenceCommands:
            if line.endswith("\\" + command + "{"):
                return True

        return False

    def _WantsCitable(self, line):
        """
        This method checks if the line given ends with a LaTeX citation
        command.

        :param line: The line of text which should be checked.
        :type line: str
        :rtype: bool
        :return: Whether or not given line end with a LaTeX citation command.
        """
        for command in self.CitationCommands:
            if line.endswith("\\" + command + "{"):
                return True

        return False

    def _CollectReferables(self, request_data):
        """
        Create the YCM compatible list of all referable objects which could be
        found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[dict[str,str]]
        :return: A list of all referable objects which could be found in a format
                 which YCM understands.

        """
        referables = self._CollectReferablesInner(request_data)

        return [ BuildCompletionData(
            r.completion(),
            extra_menu_info=r.extra_info()
            ) for r in referables ]


    def _CollectReferablesInner(self, request_data):
        """
        Create a list of all referable objects which could be found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[TexReferable]
        :return: A list of all referable objects which could be found.
        """
        referables = []

        # Get the directory where to search for the files.
        file_dir = request_data['filepath']
        if not isdir(file_dir):
            # Use the corresponding directory if the file path points to a file.
            file_dir = dirname(file_dir)

        for tex_file_name in self._GetAllTexFiles(file_dir):
            try:
                with open(tex_file_name, "r") as tex_file:
                    content = tex_file.read()

                logger.debug("Get referables from {}".format(tex_file_name))

                # Add all the referable objects which are found in the current
                # file to the overall list.
                referables.extend(self._GetAllReferables(content))

            except IOError as e:
                # The file could somehow not be opened. Skip it.
                logger.warn("Could not open {} for inspection".format(
                    tex_file_name))

        return sorted(referables)

    def _CollectCitables(self, request_data):
        """
        Create the YCM compatible list of all citable objects which could be
        found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[dict[str,str]]
        :return: A list of all citable objects which could be found in a format
                 which YCM understands.
        """
        citables = self._CollectCitablesInner(request_data)

        return [ BuildCompletionData(
            c.completion(),
            extra_menu_info=c.extra_info()
            ) for c in citables]

    def _CollectCitablesInner(self, request_data):
        """
        Create a list of all citable objects which could be found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[TexCitable]
        :return: A list of all citable objects which could be found.
        """
        citables = []
        bibliographies = []

        # Get the directory where to search for the files.
        file_dir = request_data['filepath']
        if not isdir(file_dir):
            # Use the corresponding directory if the file path points to a file.
            file_dir = dirname(file_dir)

        # 1. Scan all found tex-files for a bibliography command.
        for tex_file_name in self._GetAllTexFiles(file_dir):
            try:
                with open(tex_file_name, "r") as tex_file:
                    content = tex_file.read()

                # Add all found bib-files mentioned in this file to the
                # overall list.
                bibliographies.extend(self._GetAllBibliographies(content))

            except IOError as e:
                # The file could somehow not be opened.
                logger.warn("Could not open {} for inspection".format(
                    tex_file_name))

        # 2. Parse the corresponding Bibtex-files.
        for bib in bibliographies:
            bib_file_name = join(file_dir, bib + ".bib")

            if isfile(bib_file_name):
                # Open the file and parse it
                try:
                    with open(bib_file_name, "r") as bib_file:
                        content = bib_file.read()

                    logger.debug("Get citables from {}".format(bib_file_name))

                    # Add all citables found in this bibliography file to the
                    # overall list.
                    citables.extend(self._GetAllCitables(content))

                except IOError as e:
                    # The file could somehow not be opened.
                    logger.warn("Could not open {} for inspection".format(
                        bib_file_name))

            else:
                # The file does not exist. Ignore it.
                logger.warn("Bibliography {} does not exist".format(
                    bib_file_name))

        return sorted(citables)

    def _GetAllTexFiles(self, directory):
        """
        Get the list of all tex-files which are present in the specified
        directory.

        :param directory: The directory of interest.
        :type directory: str
        :rtype: list[str]
        :return: A list of all tex-files found in the directory.
        """
        return [join(directory, f) for f in listdir(directory)
                if isfile(join(directory, f)) and splitext(f)[1] == ".tex"]

    def _GetAllReferables(self, file_content):
        """
        Parse the given content for labels which can be later referenced.

        :param file_content: The content of the file which should be examined.
        :type file_content: str
        :rtype: list[TexReferable]
        :return: The list of all referable objects in the file.
        """
        found_referables = []

        for line_nr, line in enumerate(file_content.splitlines()):
            label = self._ExtractFromOptionOrCommand(line, "label")

            if label is not None:
                name, ref_type = self._GetAdditionalReferableInformation(
                            file_content, label)

                referable = TexReferable(label=label, name=name,
                        ref_type=ref_type)
                referable.shorten("No Name")

                found_referables.append(referable)

        return found_referables

    def _GetAdditionalReferableInformation(self, file_content, label):
        """
        Parse the given content for additional information to a given label of a
        referable object.

        :param file_content: The content of the file which should be examined.
        :type file_content: str
        :param label: The label of the referable object.
        :type label: str
        :rtype: (str,str)
        :return: A tuple containing the name and the type of the corresponding
                 referable object.
        """
        name = "No Name"
        ref_type = "unknown"

        # Search for the definition of the label in the text.
        label_pos = 0

        while True:
            label_pos = file_content.find(label, label_pos)

            # Was the label actually contained in the file?
            if label_pos == -1:
                break

            # Check that this is actually the label definition and not a
            # reference to it.
            if file_content[:label_pos].endswith("label=") or \
                    file_content[:label_pos].endswith(r"\label{"):
                # This is actually the definition so break here.
                break
            else:
                # Continue searching.
                label_pos += len(label)

        if label_pos != -1:
            # The label was found in the file. Continue to search for additional
            # information.

            # Search from the label position beginning backwards until another latex
            # command is found. If this command is either a begin or a sectioning
            # command use it to extract the data. Otherwise continue to search.
            current_pos = label_pos

            while current_pos >= 0:
                current_pos = file_content.rfind("\\", 0, current_pos)

                if current_pos == -1:
                    # Nothing could be found any more. Leave the loop
                    break

                current_content = file_content[current_pos:label_pos]

                if current_content.startswith(r"\begin{"):
                    # This is a begin command. Which begins an environment.

                    # Search inside within the environment for the caption
                    # command and extract the reference type which is the
                    # environment type.

                    # Extract the reference type.
                    ref_type = self._ExtractFromCommand(current_content, "begin")

                    # Extract the name from the environment
                    env_begin = current_pos
                    env_end = file_content.find(r"\end{" + ref_type + "", env_begin)
                    env_content = file_content[env_begin:env_end]

                    found_name = self._ExtractFromOptionOrCommand(env_content,
                            "caption")

                    if name is not None:
                        # The name of the referable object could not be
                        # determined. So use the default.
                        name = found_name

                    # Leave the search loop as the needed information is found.
                    break

                else:
                    found = False

                    # Check for all sectioning commands.
                    for command in self.SectioningCommands:
                        # Try if the command can be found in the currently
                        # examined content.
                        found_name = self._ExtractFromCommand(current_content,
                                command, starable=True)

                        if found_name is not None:
                            # The command was found and the name directly
                            # extracted. So just use extract also the reference
                            # type which is the command name and finish the
                            # search.
                            name = found_name
                            ref_type = command
                            found = True
                            break

                    # Leave the search loop as the needed information is found.
                    if found:
                        break

                    for command, command_type in self.SpecialSectioningCommands:
                        # Try if this command can be found in the currently
                        # examined content.
                        found_name = self._ExtractFromCommand(current_content,
                                command)

                        if found_name is not None:
                            # The command could be found. The name is already
                            # extracted, so just use it. The reference type is
                            # the command_type.
                            name = found_name
                            ref_type = command_type
                            found = True
                            break

                    # Leave the search loop as the needed information is found.
                    if found:
                        break

        else:
            # The label could not be found in the file. Something went wrong!
            logger.warn("Could not find additional information " + \
                    "to referable {}".format(label))

        return (name, ref_type)

    def _GetAllBibliographies(self, file_content):
        """
        Parse the given content for mentioned bibliographies and return them.

        :param file_content: The content of the file which should be examined.
        :type file_content: str
        :rtype: list[str]
        :return: The list of all bibliographies found in the file.
        """
        found_bibliographies = []

        for line in file_content.splitlines():
            # Check whether a bibliography command is in the current line.
            for command in self.BibliographyCommands:
                biblographies = self._ExtractFromCommand(line, command)

                if biblographies is not None:
                    # The command to define a bibliography is in this line.
                    # Add then to the list.
                    found_bibliographies.extend(biblographies.split(","))

        return found_bibliographies

    def _GetAllCitables(self, file_content):
        """
        Parse the given content for citable objects and return them.

        :param file_content: The content of the file which should be examined.
        :type file_content: str
        :rtype: list[TexCitable]
        :return: The list of all found citable objects.
        """
        found_citables = []

        database = bibtexparser.loads(file_content)

        for entry in database.entries:
            # Extract the needed data from the entry.
            label = entry['ID']
            title = entry['title'] if entry.has_key('title') else "No Title"
            author = entry['author'] if entry.has_key('author') else "No Author"
            cite_type = entry['ENTRYTYPE']

            citable = TexCitable(label=label, title=title, author=author,
                    cite_type=cite_type)
            citable.shorten("No Title", "No Author")

            found_citables.append(citable)

        return found_citables


###
# Enable the file to be runnable as script, too.
###
if __name__ == "__main__":
    # Additional imports:
    from os import getcwd
    from os.path import isabs, expanduser
    from argparse import ArgumentParser

    # Command line options for the script.
    options = ArgumentParser(prog="tex_completer",
            description="A semantic completer for YCM supporting TeX files")

    options.add_argument('directory', type=str, nargs=1,
            help="The base directory for the completer to look for files.")
    print_type = options.add_mutually_exclusive_group()
    print_type.add_argument('-s', '--shortened', default=False,
            action='store_true', dest='shortened',
            help="Present the information in their shortened version.")
    print_type.add_argument('-f', '--full', default=False,
            action='store_true', dest='full',
            help="Present all information available.")

    # Get the option and make properly usable.
    parsed_args = options.parse_args()

    directory = parsed_args.directory[0]
    if "~" in directory:
        directory = expanduser(directory)
    if not isabs(directory):
        directory = join(getcwd(), directory)

    shortened = parsed_args.shortened
    full = parsed_args.full

    # Run the completer and get all citable and referable latex objects found in
    # the directory.
    completer = TexCompleter({
        'min_num_of_chars_for_completion' : 1,
        'auto_trigger' : False
    })

    citables = completer._CollectCitablesInner(
            {'filepath' : directory}
    )
    referables = completer._CollectReferablesInner(
            {'filepath' : directory}
    )

    print("Citables (" + str(len(citables)) + "):")
    for c in citables:
        if full:
            print(u"{label}: {title} - {author} ({cite_type} - {abbr})".format(
                label=c._label, title=c._title, author=c._author,
                cite_type=c._cite_type, abbr=c._abbreviation)
            )
        else:
            print(u"{completion}: {extra_info}".format(
                completion=c.completion(), extra_info=c.extra_info(shortened))
            )

    print("")
    print("Referables (" + str(len(referables)) + "):")
    for r in referables:
        if full:
            print(u"{label}: {name} ({ref_type} - {abbr})".format(label=r._label,
                name=r._name, ref_type=r._ref_type, abbr=r._abbreviation))
        else:
            print(u"{completion}: {extra_info}".format(
                completion=r.completion(), extra_info=r.extra_info(shortened))
            )

# vim: ft=python tw=80 expandtab tabstop=4
