import mimetypes
import os
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
import markdown
import pymdownx.superfences
import pymdownx.arithmatex as arithmatex


class MarkdownHTTPRequestHandler(BaseHTTPRequestHandler):
    content_type = 'text/html;charset=utf-8'
    stylesheet_content_type = 'text/css'
    encoding = 'utf8'
    stylesheet = 'markdown.css'
    favicon = 'favicon.ico'

    def do_GET(self):
        path = self.path[1:]

        if path == 'markdown.css':
            return self.stylesheet_response()
        elif path == 'favicon.ico':
            return self.favicon_response()

        if not os.path.isdir(self.server.directory):
            return self.markdown_file(self.server.directory)

        full_path = os.path.join(self.server.directory, path)

        if not os.path.exists(full_path):
            self.send_error(404, "File not found")

        if os.path.isdir(full_path):
            content = []
            for entry in os.listdir(full_path):
                content.append(
                    '<div><a href="{}">{}</a>'.format(
                        os.path.join(path, entry),
                        entry
                    )
                )
            return self.make_html(content)

        # Finally, try parsing the file as markdown
        return self.markdown_file(full_path)

    def make_html(self, content, last_modified=None):
        full_page = [
            "<!doctype html>",
            "<html><head>",
        ]
        full_page.extend(self.header_content())
        full_page.extend(["</head>", "<body>"])
        full_page.extend(content)
        full_page.append("</body></html>")

        text = "\n".join(full_page)
        self.send_response(200)
        self.send_header("Content-type", self.content_type)

        if last_modified is not None:
            self.send_header("Last-Modified",
                             self.date_time_string(last_modified))

        self.send_header("Content-Length", len(text))
        self.end_headers()
        self.wfile.write(text.encode(self.encoding))

    def markdown_file(self, path):
        with open(path, 'r', encoding='UTF-8') as f:
            fs = os.fstat(f.fileno())
            return self.make_html(
                [markdown.markdown(f.read(),
                                   extensions=['toc', 'meta',
                                               'pymdownx.betterem',  # pip install pymdown-extensions
                                               'pymdownx.superfences',
                                               'pymdownx.arithmatex',
                                               'pymdownx.inlinehilite',
                                               'pymdownx.tabbed',
                                               'pymdownx.tasklist',
                                               'markdown.extensions.footnotes',
                                               'markdown.extensions.attr_list',
                                               'markdown.extensions.def_list',
                                               'markdown.extensions.tables',
                                               'markdown.extensions.abbr',
                                               'markdown.extensions.md_in_html',
                                               ],
                                   extension_configs={
                                       'pymdownx.superfences': {
                                           'custom_fences': [
                                               {
                                                   'name': 'mermaid',
                                                   'class': 'mermaid',
                                                   'format': pymdownx.superfences.fence_div_format
                                               }
                                           ]
                                       },
                                       'pymdownx.inlinehilite': {
                                           'custom_inline': [
                                               {
                                                   'name': 'math',
                                                   'class': 'arithmatex',
                                                   'format': arithmatex.inline_mathjax_format
                                               }
                                           ]
                                       },
                                       'pymdownx.tasklist': {
                                           'custom_checkbox': True,
                                           'clickable_checkbox': False
                                       }
                                   },
                                   )],
                last_modified=fs.st_mtime
            )

    def header_content(self):
        return [
            '<link href="{}" rel="stylesheet"></link>'.format('/' + self.stylesheet),
            '<script src="https://unpkg.com/mermaid@8.6.4/dist/mermaid.min.js"></script>',
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js"></script>',
            '''
            <script>
            MathJax.Hub.Config({
              config: ["MMLorHTML.js"],
              jax: ["input/TeX", "output/HTML-CSS", "output/NativeMML"],
              extensions: ["MathMenu.js", "MathZoom.js"]
            });
            </script>''',
        ]

    def stylesheet_response(self):
        return self.serve_file(self.stylesheet, mimetypes.types_map['.css'])

    def favicon_response(self):
        return self.serve_file(self.favicon, mimetypes.types_map['.ico'])

    def serve_file(self, filename, content_type):
        """
        Returns a 200 response with the content of the filename (which is
        relative to this file), and the given content type.
        """
        rel_path = os.path.join(os.path.dirname(__file__), filename)

        with open(rel_path, 'rb') as f:
            self.send_response(200)
            self.send_header("Content-type", content_type)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                             self.date_time_string(fs.st_mtime))
            self.end_headers()

            shutil.copyfileobj(f, self.wfile)


class MarkdownHTTPServer(HTTPServer):
    handler_class = MarkdownHTTPRequestHandler

    def __init__(self, server_address, directory):
        self.directory = directory

        try:
            super().__init__(
                server_address, self.handler_class
            )
        except TypeError:
            # Python 2.7 will cause a type error, and in addition
            # HTTPServer is an old-school class object, so use the old
            # inheritance way here.
            HTTPServer.__init__(self, server_address, self.handler_class)


def run(host='', port=8080, directory=os.getcwd()):
    server_address = ('', port)
    httpd = MarkdownHTTPServer(server_address, directory)
    print("Serving from http://{}:{}/".format(host, port))
    httpd.serve_forever()