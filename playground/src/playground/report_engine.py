# expected findings: OCP (isinstance if/elif ladder with >= 3 branches),
# docstrings.1 (missing docstrings), classes.3 (five classes in one file).


class HtmlReport:
    pass


class CsvReport:
    pass


class JsonReport:
    pass


class XmlReport:
    pass


class ReportEngine:
    def render(self, report):
        if isinstance(report, HtmlReport):
            return f"<html><body>{report.body}</body></html>"
        elif isinstance(report, CsvReport):
            return "\n".join(report.rows)
        elif isinstance(report, JsonReport):
            return report.payload
        elif isinstance(report, XmlReport):
            return f"<report>{report.body}</report>"
        raise ValueError(f"unknown report: {type(report)}")
