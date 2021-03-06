import re
import pywikibot
import pywikibot.textlib as textlib
from scripts.upload import UploadRobot
from scripts.data_ingestion import DataIngestionBot
from argparse import ArgumentParser

def UploadBotArgumentParser():
    """Create an ArgumentParser object."""
    parser = ArgumentParser(description="Process metadata and upload to Commons")
    parser.add_argument('--prepare-alignment', action="store_true",
                        help='Prepare the alignment.')
    parser.add_argument('--post-process', action="store_true",
                        help='Post-process the files - necessary for upload.')
    parser.add_argument('--dry-run', action="store_true",
                        help='Do not do the upload, just debug.')
    parser.add_argument('--upload', action="store_true",
                        help='Upload the file to Wikimedia Commons.')
    return parser


class DataIngestionBot(DataIngestionBot):

    """Overload of DataIngestionBot."""

    def __init__(self, reader, front_titlefmt, rear_titlefmt,
                 variable_titlefmt, pagefmt,
                 subst=False,
                 verifyDescription=True,
                 site=pywikibot.getSite(u'commons', u'commons')):
        self.reader = reader
        self.front_titlefmt = front_titlefmt
        self.rear_titlefmt = rear_titlefmt
        self.variable_titlefmt = variable_titlefmt
        self.pagefmt = pagefmt
        self.subst = subst
        self.verifyDescription = verifyDescription
        if subst:
            self.pagefmt = 'subst:%s' % self.pagefmt
        self.site = site
        #super(self.__class__, self).__init__()

    def _doUpload(self, photo):
        duplicates = photo.findDuplicateImages(self.site)
        if duplicates:
            pywikibot.output(u"Skipping duplicate of %r" % (duplicates, ))
            return duplicates[0]
        if self.subst:
            photo.metadata['subst'] = 'subst:'
        title = make_title(photo.metadata, self.front_titlefmt,
                           self.rear_titlefmt, self.variable_titlefmt)

        description = textlib.glue_template_and_params((self.pagefmt,
                                                        photo.metadata))

        bot = UploadRobot(url=photo.URL,
                          description=description,
                          useFilename=title,
                          keepFilename=True,
                          verifyDescription=self.verifyDescription,
                          uploadByUrl=False,
                          targetSite=self.site)
        bot._contents = photo.downloadPhoto().getvalue()
        bot._retrieved = True

        print title
        print description
        bot.run()

        return title

    def _debug_description(self, photo):
        """Print the description for debugging."""
        title = make_title(photo.metadata, self.front_titlefmt,
                           self.rear_titlefmt, self.variable_titlefmt)
        if self.subst:
            photo.metadata['subst'] = 'subst:'
        description = textlib.glue_template_and_params((self.pagefmt,
                                                        photo.metadata))
        print "= %s =" % title
        print "{{collapse|title=%s|1=<pre>\n%s\n</pre>}}" % (title,
                                                             description)
        print description

    def dry_run(self):
        """Dry-run, without uploading."""
        for photo in self.reader:
            self._debug_description(photo)


def _cut_title(fixed_front, variable, fixed_rear, MAX_LENGTH=240):
    """Return the given title smartly cut"""
    fixed_length = len(fixed_front) + len(fixed_rear)
    available_length = MAX_LENGTH - fixed_length
    chunked = variable.split()
    part = 1
    while len(variable) > available_length:
        variable = " ".join(chunked[:-part]) + "..."
        part += 1
    title = fixed_front + variable + fixed_rear
    assert len(title) <= MAX_LENGTH
    return title


def make_title(entries, fixed_front_fmt, fixed_rear_fmt, variable_fmt):
    """Return a title based on the metadata and format strings.

    This method uses three format strings: the fixed front, the variable,
    and the fixed rear.

    """
    fixed_front = fixed_front_fmt % entries
    extension = entries.get('_ext', 'none').lower()
    if extension is None:
        extension = 'none'
    fixed_rear = fixed_rear_fmt % entries + '.' + extension
    variable = variable_fmt % entries
    return cleanUpTitle(_cut_title(fixed_front, variable, fixed_rear,
                                   MAX_LENGTH=240))


def cleanUpTitle(title):
    """Clean up the title of a potential mediawiki page.

    Otherwise the title of the page might not be allowed by the software.

    """
    title = title.strip()
    title = re.sub(u"^- ", u"", title)
    title = re.sub(u"^ - ", u"", title)
    title = re.sub(u"[<{\\[]", u"(", title)
    title = re.sub(u"[>}\\]]", u")", title)
    title = re.sub(u"[ _]?\\(!\\)", u"", title)
    title = re.sub(u",:[ _]", u", ", title)
    title = re.sub(u"[;:][ _]", u", ", title)
    title = re.sub(u"[\t\n ]+", u" ", title)
    title = re.sub(u"[\r\n ]+", u" ", title)
    title = re.sub(u"[\n]+", u"", title)
    title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
    title = re.sub(u"[&#%?!]", u"^", title)
    title = re.sub(u"[;]", u",", title)
    title = re.sub(u"[/+\\\\:]", u"-", title)
    title = re.sub(u"--+", u"-", title)
    title = re.sub(u",,+", u",", title)
    title = re.sub(u" ,+", u",", title)
    title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
    title = title.replace(u"  ", u" ")
    title = title.replace(u" ", u"_")
    title = re.sub(u"-_-", u"-", title)
    return title
