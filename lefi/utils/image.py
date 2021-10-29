import base64
import imghdr

__all__ = (
    "get_mimetype",
    "bytes_to_data_uri",
)


def get_mimetype(data: bytes) -> str:
    """
    Get the mimetype of the given data.

    Parameters:
        data (bytes): The data to get the mimetype of.

    Returns:
        The mimetype of the data.
    """
    type_ = imghdr.what(file=None, h=data)
    if not type_:
        raise ValueError("Unable to determine image type")

    if type_ not in ("jpeg", "png", "gif"):
        raise ValueError("Unsupported image type")

    return f"image/{type_}"


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
