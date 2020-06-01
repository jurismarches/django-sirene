from io import StringIO


class FakeOpenFile:
    def __enter__(self, *args):
        return StringIO("")

    def __exit__(self, *args):
        pass


class FakeZfile:
    def namelist(self):
        return ["name.csv"]

    def open(self, *args):
        return FakeOpenFile()

    def close(self):
        return
