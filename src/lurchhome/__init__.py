try:
    import importlib.metadata

    __version__ = importlib.metadata.version('lurchhome')
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
