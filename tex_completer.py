#!/usr/bin/env python2
#
# TexCompleter - Semantic completer for YouCompleteMe which handles Tex files.
# Copyright (C) 2015 Till Smejkal
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

from __future__ import print_function

from os.path import dirname, join, isfile, splitext
from os import listdir

from ycmd.completers.completer import Completer
from ycmd import responses

import bibtexparser


class TexReferable:

    def __init__(self, label, name="Unknown", ref_type="Unknown"):
        """
        Constructor

        :param label: The identifier which is used to reference it in the text.
        :type label: str
        :param name: The actual name of the referable object.
        :type name: str
        :param ref_type: The type of the referable object.
        """
        self.label = label
        self.name = name
        self.ref_type = ref_type


class TexCitable:

    def __init__(self, label, title="Unknown", author="Unknown",
            cite_type="Unknown"):
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
        self.label = label
        self.title = title
        self.author = author
        self.cite_type = cite_type


class TexCompleter(Completer):

    ###
    # List of Latex commands and options known by the completer.
    ###
    BibliographyCommands = ["bibliography"]
    ReferenceCommands = ["ref", "refv"]
    CitationCommands = ["cite", "citep", "citev"]
    SectioningCommands = ["chapter", "section", "subsection", "subsubsection",
            "paragraph", "subparagraph"]

    ###
    # List of supported VIM file types
    ###
    FileTypes = ["tex", "plaintex"]

    ###
    # Action which the completer supports
    ###
    # TODO: Make it an enum.
    ACTION_NONE = 0
    ACTION_REFERENCE = 1
    ACTION_CITATION = 2

    def __init__(self, user_options):
        super(TexCompleter, self).__init__(user_options)

        self._action = self.ACTION_NONE

    def DebugInfo(self, request_data):
        file_name = request_data['filepath']

        return "TeX Completer for {}".format(file_name)

    def SupportedFiletypes(self):
        return FileTypes

    def ShouldUseNowInner(self, request_data):
        self._action = self.ACTION_NONE

        # Extract the last command
        current_line = request_data['line_value']
        word_start = request_data['start_column']

        # As according to the documentation the start_column points to the
        # begin of the word which is currently typed, the last command ends
        # at exactly this position.
        last_command = current_line[:word_start]

        if self._WantsReferable(last_command):
            self._action = self.ACTION_REFERENCE

            return True

        elif self._WantsCitable(last_command):
            self._action = self.ACTION_CITATION

            return True

        return False

    def ComputeCandidatesInner(self, request_data):
        if self._action == self.ACTION_CITATION:
            return self._CollectCitables(request_data)
        elif self._action == self.ACTION_REFERENCE:
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
        Create a list of all referable objects which could be found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[TexReferable]
        :return: A list of all referable objects which could be found.
        """
        referables = []
        file_dir = dirname(request_data['filepath'])

        for tex_file_name in self._GetAllTexFiles(file_dir):
            try:
                with open(tex_file_name, "r") as tex_file:
                    content = tex_file.read()

                # Add all the referable objects which are found in the current
                # file to the overall list.
                referables.extend(self._GetAllReferables(content))

            except IOError as e:
                # The file could somehow not be opened. Skip it.

                # TODO: Log the exception.
                pass

        return referables

    def _CollectCitables(self, request_data):
        """
        Create a list of all citable objects which could be found.

        :param request_data: The data which YouCompleteMe passes to the
                             completer.
        :type request_data: dict[str,str]
        :rtype: list[TexCitable]
        :return: A list of all citable objects which could be found.
        """
        citables = []
        file_dir = dirname(request_data['filepath'])

        bibliographies = []

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

                # TODO: Log the exception.
                pass

        # 2. Parse the corresponding Bibtex-files.
        for bib in bibliographies:
            bib_file_name = join(file_dir, bib + ".bib")

            if isfile(bib_file_name):
                # Open the file and parse it
                try:
                    with open(bib_file_name, "r") as bib_file:
                        content = bib_file.read()

                    # Add all citables found in this bibliography file to the
                    # overall list.
                    citables.extend(self._GetAllCitables(content))

                except IOError as e:
                    # The file could somehow not be opened.

                    # TODO: Log the exception.
                    pass

            else:
                # The file does not exist. Ignore it.

                # TODO: Log that the file did not exist.
                pass

        return citables

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
                name, ref_type = self._GetAdditionalReferenceInformation(
                            file_content, label)

                found_referables.append(TexReferable(label=label, name=name,
                    ref_type=ref_type))

        return found_referables

    def _GetAdditionalReferenceInformation(self, file_content, label):
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
        label_pos = file_content.find(label)
        name = "No Name"
        ref_type = "unknown"

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

        else:
            # The label could not be found in the file. Something went wrong!

            # TODO: Log that this happened.
            pass

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
            title = entry['title'] if entry.has_key('title') else 'No Title'
            author = entry['author'] if entry.has_key('author') else 'No Author'
            cite_type = entry['ENTRYTYPE']

            found_citables.append(TexCitable(label=label, title=title,
                author=author, cite_type=cite_type))

        return found_citables


# Enable the file to be runnable as script, too.
if __name__ == "__main__":
    import argparse
    from os import getcwd
    from os.path import isabs

    arguments = argparse.ArgumentParser(prog="tex_completer",
            description="A semantic completer for YCM supporting TeX files")

    arguments.add_argument('directory', type=str, nargs=1,
            help="The base directory for the completer to look for files.")

    args = arguments.parse_args()
    dic = args.directory[0]

    directory = join(getcwd(), dic) if not isabs(dic) else dic

    completer = TexCompleter({
        'min_num_of_chars_for_completion' : 1,
        'auto_trigger' : False
    })

    citables = completer._CollectCitables(
            {'filepath' : join(directory, "foo.txt")}
    )
    referables = completer._CollectReferables(
            {'filepath' : join(directory, "foo.txt")}
    )

    print("The following things have been found!")

    print("\nCitables (" + str(len(citables)) + "):")
    for c in citables:
        print(u"{label}: {title} - {author} ({cite_type})".format(
            label=c.label, title=c.title, author=c.author,
            cite_type=c.cite_type))

    print("\nReferables (" + str(len(referables)) + "):")
    for r in referables:
        print(u"{label}: {name} ({ref_type})".format(label=r.label,
            name=r.name, ref_type=r.ref_type))

# vim: ft=python tw=80 expandtab tabstop=4
