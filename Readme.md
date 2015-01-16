LaTeX Completer for YouCompleteMe
=================================

The [YCM](https://github.com/Valloric/YouCompleteMe "YouCompleteMe") VIM plugin allows
integration of other completers. So for example for C++ or other languages. This completer
adds support for the LaTeX programming language. It uses directly the completer API of YCM
and thereby supports all the features which the plugin itself provides.


Supported Completions
---------------------

Currently the completer has support for the following commands:

1. References to other LaTeX objects via '\ref' and '\refv'. Therefore all '.tex' files in the
   current directory are scanned and all defined labels are gathered. For each label additional
   information such as the actual caption of the object and its type ('chapter', 'figure', etc.)
   are collected and later shown in the completion menu.

2. Citations of other work via '\cite', '\citep', and '\citev'. Therefore again all '.tex' files
   in the current directory are scanned for the definition of the Bibtex-database files. These
   files are then scanned too and all entries are extracted. These entries will be presented in
   the completion menu together with additional information such as the authors, title, and the
   type of the Bibtex-entry ('book', 'article', etc.).


Installation
------------


Limitations and Future Work
---------------------------

1. The completer currently only supports Bibtex databases for citation completion. Support for
   other formats should be added in the future.

2. The additional information collection for referable objects is kind of hacky. It uses heavy
   string manipulation to find the information. A proper LaTeX parser may be appropriate here.
   Though, this might be an overkill for this purpose.

3. Support for other LaTeX commands like abbreviations and glossary entries can be added in
   the future to make this completer more attractive. This might need a refactoring of the
   current design.

4. The completer currently only finds '.tex' files which are located in the same directory as
   the one which is edited at the same moment. It may be interesting to also parse '\input'
   and '\include' commands and thereby somehow circumvent this problem. Or one could search also
   in parent and subdirectories and use the commands to build dependencies between the files and
   then only parse those files which are correlated to the current one.

5. In the current version the completer parses all files it finds again if it is executed. This
   can be quite intensive if there a many '.tex' files. Hence, some kind of buffer could be used
   here. However changes to other files which must be detected which can become tricky.

6. At the moment the plugin only provides a completer. However I could also imagine a
   "GoToDefinition" functionality similar to the one of C++-completers. For this functionality the
   buffer mentioned in 5. would be really handy.
