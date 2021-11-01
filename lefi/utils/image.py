import base64

__all__ = (
    "is_jpeg",
    "is_png",
    "is_gif",
    "get_mimetype",
    "bytes_to_data_uri",
)


def is_jpeg(data: bytes) -> bool:
    """
    Check if the data is a JPEG image.

    Parameters:
        data (bytes): The data to check.

    Returns:
        True if the data is a JPEG image, False otherwise.

    """
    return data[6:10] in (b"JFIF", b"Exif")


def is_png(data: bytes) -> bool:
    """
    Check if the given data is a PNG.

    Parameters:
        data (bytes): The data to check.

    Returns:
        True if the data is a PNG, False otherwise.

    """
    return data[:8] == b"\211PNG\r\n\032\n"


def is_gif(data: bytes) -> bool:
    """
    Check if the given data is a GIF.

    Parameters:
        data (bytes): The data to check.

    Returns:
        True if the data is a GIF, False otherwise.

    """
    return data[:6] in (b"GIF87a", b"GIF89a")


def get_mimetype(data: bytes) -> str:
    """
    Get the mimetype of the given data.

    Parameters:
        data (bytes): The data to get the mimetype of.

    Returns:
        The mimetype of the data.
    """
    if is_jpeg(data):
        return "image/jpeg"
    elif is_png(data):
        return "image/png"
    elif is_gif(data):
        return "image/gif"
    else:
        raise ValueError("Unknown image type")


def bytes_to_data_uri(data: bytes) -> str:
    """
    Convert the given bytes to a URI.

    Parameters:
        data (bytes): The data to convert.

    Returns:
        The data URI.
    """
    uri = "data:{mime};base64,{data}"
    mime = get_mimetype(data)

    b64 = base64.b64encode(data).decode("ascii")
    return uri.format(mime=mime, data=b64)
