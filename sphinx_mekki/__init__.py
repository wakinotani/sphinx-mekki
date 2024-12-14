""" sphinx-mekki """

from __future__ import annotations
import os
import base64
import html
import rjsmin
import cssutils
import mimetypes
import shutil
from typing import Any
from docutils import nodes
from docutils.nodes import Node
from docutils.nodes import Element
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.util import isurl, logging
from sphinx.transforms.post_transforms.images import ImageConverter
from sphinx.builders.html import JavaScript, Stylesheet
from sphinx.writers.html import HTML5Translator
from sphinx.environment import BuildEnvironment
from sphinx.environment.collectors.toctree import TocTreeCollector
from sphinx.util.images import get_image_size

__version__ = "0.8.3"

logger = logging.getLogger(__name__)


def guess_mimetype(filename: str) -> str:
    mimetype = mimetypes.guess_type(filename, strict=False)[0]
    return mimetype


def convert_to_base64_str(filename: str) -> str:
    if not hasattr(convert_to_base64_str, "cache"):
        convert_to_base64_str.cache = {}
    if filename in convert_to_base64_str.cache:
        return convert_to_base64_str.cache[filename]
    ret = base64.b64encode(open(filename, "rb").read()).decode("utf-8")
    convert_to_base64_str.cache[filename] = ret
    return ret


def convert_to_data_uri(filename: str) -> str:
    mimetype = guess_mimetype(filename)
    data_uri = "data:{};base64,{}".format(mimetype, convert_to_base64_str(filename))
    return data_uri


def embed_favicon(app: Sphinx, pagename: str, templatename: str, context: dict, doctree: Node) -> None:
    favicon_url = app.builder.globalcontext["favicon_url"]
    if favicon_url and not isurl(favicon_url):
        # convert favicon file to data_URI
        favicon_path = os.path.join(app.srcdir, favicon_url)
        context["favicon_url"] = convert_to_data_uri(favicon_path)


def embed_logo(app: Sphinx, pagename: str, templatename: str, context: dict, doctree: Node) -> None:
    logo_url = app.builder.globalcontext["logo_url"]
    if logo_url and not isurl(logo_url):
        # convert logo file to data_URI
        logo_path = os.path.join(app.srcdir, logo_url)
        context["logo_url"] = convert_to_data_uri(logo_path)


def setup_css_tag_helper(app: Sphinx, pagename: str, templatename: str, context: dict, doctree: Node) -> None:

    if not hasattr(setup_css_tag_helper, "cache"):
        setup_css_tag_helper.cache = {}
    pathto = context.get("pathto")

    def parse_css(sheet: cssutils.css.CSSStyleSheet) -> str:
        out = ""
        for rule in sheet.cssRules:
            if rule.type == cssutils.css.CSSRule.IMPORT_RULE:
                css_path = os.path.abspath(os.path.join(app.outdir, "_static", rule.href))
                css_imported = open(css_path, encoding="utf-8").read()
                sheet_imported = cssutils.parseString(css_imported)
                out += parse_css(sheet_imported)
            elif not (rule.cssText is None or rule.cssText == ""):
                out += rule.cssText
                out += "\n"
        return out

    def css_tag(css: Stylesheet) -> str:
        if css in setup_css_tag_helper.cache:
            return setup_css_tag_helper.cache[css]
        attrs = []
        for key in sorted(css.attributes):
            value = css.attributes[key]
            if value is not None:
                attrs.append(f'{key}="{html.escape(value, True)}"')
        uri = pathto(css.filename, resource=True)
        attrs.append(f'href="{uri}"')

        css_path = os.path.abspath(os.path.join(app.outdir, os.path.dirname(pagename), uri))

        css_basename = os.path.basename(css.filename)
        if css_basename == "pygments.css":
            body = app.builder.highlighter.get_stylesheet()
        else:
            body = open(css_path, encoding="utf-8").read()

        cssutils.ser.prefs.useMinified()
        sheet = cssutils.parseString(body)
        body = parse_css(sheet)

        # ret = '<style type="text/css">\n{}</style>'.format(body)
        ret = '<style type="text/css">{}</style>'.format(body.replace("\n", ""))
        setup_css_tag_helper.cache[css] = ret
        return ret

    context["css_tag"] = css_tag


def setup_js_tag_helper(app: Sphinx, pagename: str, templatename: str, context: dict, doctree: Node) -> None:

    if not hasattr(setup_js_tag_helper, "cache"):
        setup_js_tag_helper.cache = {}
    pathto = context.get("pathto")

    def js_tag(js: JavaScript) -> str:
        if js in setup_js_tag_helper.cache:
            return setup_js_tag_helper.cache[js]
        attrs = []
        body = ""
        if isinstance(js, JavaScript):
            for key in sorted(js.attributes):
                value = js.attributes[key]
                if value is not None:
                    if key == "body":
                        body = value
                    elif key == "data_url_root":
                        attrs.append(f'data-url_root="{pathto("", resource=True)}"')
                    else:
                        attrs.append(f'{key}="{html.escape(value, True)}"')
            if js.filename:
                uri = pathto(js.filename, resource=True)
                js_path = os.path.abspath(os.path.join(app.outdir, os.path.dirname(pagename), uri))

                if not os.path.exists(js_path):
                    logger.warning("[sphinx_mekki] js_path={} not found".format(js_path))
                else:
                    body = open(js_path, encoding="utf-8").read()
                body = rjsmin.jsmin(body)

        else:
            # str value (old styled)
            attrs.append(f'src="{pathto(js, resource=True)}"')

        ret = ""
        if attrs:
            ret = f'<script {" ".join(attrs)}>{body}</script>'
        else:
            ret = f"<script>{body}</script>"
        setup_js_tag_helper.cache[js] = ret
        return ret

    context["js_tag"] = js_tag


class MekkiImageConverter(ImageConverter):

    default_priority = 200

    def match(self, node: Node) -> bool:
        if self.app.builder.supported_image_types == []:
            return False
        else:
            return self.app.builder.supported_data_uri_images

    def handle(self, node: Node) -> None:
        try:
            node["alt"] = node["uri"]
            path = os.path.join(self.app.srcdir, node["uri"])
            node["uri"] = convert_to_data_uri(path)
            # node having a scale attribute, but neither width nor height
            if "scale" in node:
                if not ("width" in node or "height" in node):
                    size = get_image_size(path)
                    node["width"] = str(size[0])
                    node["height"] = str(size[1])
        except Exception as e:
            logger.error(e)


def add_static_path(app: Sphinx) -> None:
    app.config.html_static_path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "_static"))


download_index = {}


class download_reference(Element):
    pass


def visit_download_reference_html(writer: MekkiHTML5Translator, node: Element) -> None:

    global download_index

    if writer.builder.current_docname not in download_index:
        # key is not in the dict
        download_index[writer.builder.current_docname] = 0
    download_index[writer.builder.current_docname] += 1

    path = os.path.join(writer.builder.srcdir, os.path.dirname(writer.builder.current_docname))
    path = os.path.join(path, node["reftarget"])
    path = os.path.normpath(path)
    basename = os.path.basename(path)
    mimetype = guess_mimetype(path)
    base64_str = convert_to_base64_str(path)

    script_atts = {"type": "text/javascript"}
    writer.body.append(writer.starttag(node, "script", "", **script_atts))
    writer.body.append("var content_%d = '%s';" % (download_index[writer.builder.current_docname], base64_str))
    writer.body.append("</script>\n")

    atts = {
        "class": "reference download embed",
        "href": "#",
        "ids": [],
        "onclick": "",
        "download": "",
    }
    atts["ids"] = ["content_%d" % download_index[writer.builder.current_docname]]
    atts["href"] = "#" + basename
    atts["download"] = basename
    atts["onclick"] = "mekki_handle_download(content_%d, '%s', 'content_%d')" % (
        download_index[writer.builder.current_docname],
        mimetype,
        download_index[writer.builder.current_docname],
    )
    writer.body.append(writer.starttag(node, "a", "", **atts))


def depart_download_reference_html(writer: MekkiHTML5Translator, node: Element) -> None:
    writer.body.append("</a>")


class MekkiHTML5Translator(HTML5Translator):

    # override sphinx.writers.html.HTML5Translator.get_secnumber
    def get_secnumber(self, node: Element) -> tuple[int, ...] | None:
        # modify not to use node['secnumber']
        # if node.get('secnumber'):
        #    return node['secnumber']

        if isinstance(node.parent, nodes.section):
            if self.builder.name == "singlehtml":
                docname = self.docnames[-1]
                anchorname = "{}/#{}".format(docname, node.parent["ids"][0])
                if anchorname not in self.builder.secnumbers:
                    anchorname = "%s/" % docname  # try first heading which has no anchor
            else:
                anchorname = "#" + node.parent["ids"][0]
                if anchorname not in self.builder.secnumbers:
                    anchorname = ""  # try first heading which has no anchor

            if self.builder.secnumbers.get(anchorname):
                return self.builder.secnumbers[anchorname]
        elif isinstance(node, nodes.reference):
            if node.get("secnumber") and node.get("internal") and node.get("refuri"):
                anchorname = ""
                if node.get("anchorname"):
                    anchorname = node["anchorname"]
                return self.builder.secnumbers.get(anchorname)

        return None

    # override sphinx.writers.html.HTML5Translator.visit_reference
    def visit_reference(self, node: Element) -> None:
        atts = {"class": "reference"}
        if node.get("internal") or "refuri" not in node:
            atts["class"] += " internal"
        else:
            atts["class"] += " external"
        if "refuri" in node:
            atts["href"] = node["refuri"] or "#"
            if self.settings.cloak_email_addresses and atts["href"].startswith("mailto:"):
                atts["href"] = self.cloak_mailto(atts["href"])
                self.in_mailto = True
        else:
            assert "refid" in node, 'References must have "refuri" or "refid" attribute.'
            atts["href"] = "#" + node["refid"]
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)  # NoQA: PT018
            atts["class"] += " image-reference"
        if "reftitle" in node:
            atts["title"] = node["reftitle"]
        if "target" in node:
            atts["target"] = node["target"]
        self.body.append(self.starttag(node, "a", "", **atts))

        if isinstance(node.parent, nodes.TextElement):
            # modified to use get_secnumber(node) instead of node['secnumber']
            secnumber = self.get_secnumber(node)
            if secnumber:
                self.body.append(("%s" + self.secnumber_suffix) % ".".join(map(str, secnumber)))


class MekkiTocTreeCollector(TocTreeCollector):

    def assign_section_numbers(self, env: BuildEnvironment) -> list[str]:

        def _walk_toc(node: Element) -> None:
            for subnode in node.children:
                if isinstance(subnode, nodes.bullet_list):
                    _walk_toc(subnode)
                elif isinstance(subnode, nodes.list_item):
                    _walk_toc(subnode)
                elif isinstance(subnode, addnodes.only):
                    _walk_toc(subnode)
                elif isinstance(subnode, addnodes.toctree):
                    _walk_toctree(subnode)

        def _walk_toctree(toctreenode: addnodes.toctree) -> None:
            for _title, ref in toctreenode["entries"]:
                if ref in env.tocs:
                    _walk_toc(env.tocs[ref])
                    rewrite_needed.append(ref)

        if env.toc_secnumbers:
            for docname in env.toc_secnumbers:
                keys = list(env.toc_secnumbers[docname])
                if keys:
                    remove_len = len(env.toc_secnumbers[docname][keys[0]])
                    for key in keys:
                        env.toc_secnumbers[docname][key] = env.toc_secnumbers[docname][key][remove_len:]
        rewrite_needed = []
        return rewrite_needed

    def assign_figure_numbers(self, env: BuildEnvironment) -> list[str]:

        if env.toc_fignumbers:
            for docname in env.toc_fignumbers:
                for figtype in env.toc_fignumbers[docname]:
                    for i, fig_id in enumerate(env.toc_fignumbers[docname][figtype]):
                        env.toc_fignumbers[docname][figtype][fig_id] = (i + 1,)
        rewrite_needed = []
        return rewrite_needed


def build_finished(app: Sphinx, exception: Exception) -> None:

    # remove outdir/_static
    d = os.path.join(app.outdir, "_static")
    if os.path.exists(d):
        shutil.rmtree(d)

    # remove outdir/_downloads
    d = os.path.join(app.outdir, "_downloads")
    if os.path.exists(d):
        shutil.rmtree(d)


def update_page_context(app: Sphinx, pagename: str, templatename: str, context: dict, doctree: Node) -> None:
    if "display_toc" in context:
        context["display_toc"] = app.builder.env.toc_num_entries[pagename] > 0


def setup(app: Sphinx) -> dict[str, Any]:

    # add mekki_simple theme
    app.add_html_theme(
        "mekki",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "themes", "mekki"),
    )

    # embed image/figure directives
    app.add_post_transform(MekkiImageConverter)
    # embed favicon, logo
    app.connect("html-page-context", embed_favicon)
    app.connect("html-page-context", embed_logo)

    # suppress cssutils logging messages
    import logging

    cssutils.log.setLevel(logging.CRITICAL)
    # embed css
    app.connect("html-page-context", setup_css_tag_helper)

    # embed js
    app.connect("html-page-context", setup_js_tag_helper)

    # embed download directives
    app.connect("builder-inited", add_static_path)
    app.add_js_file("mekki_handle_download.js")
    app.add_node(
        download_reference,
        html=(visit_download_reference_html, depart_download_reference_html),
        override=True,
    )

    # support mekki style section numbers
    app.add_env_collector(MekkiTocTreeCollector)
    app.set_translator("html", MekkiHTML5Translator)

    # localtoc
    app.connect("html-page-context", update_page_context)

    # remove unused files
    app.connect("build-finished", build_finished, priority=950)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
