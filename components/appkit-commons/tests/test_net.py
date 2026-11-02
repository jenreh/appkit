import pytest

from appkit_commons.net import UnsafeURLError, assert_public_http_url
from appkit_commons.testing import TEST_PASSWORD


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x.png",
        "http://",
        f"http://user:{TEST_PASSWORD}@example.com/x.png",
        "http://127.0.0.1/x.png",
        "http://localhost:8080/x.png",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/x.png",
        "http://192.168.1.1/x.png",
        "http://[::1]/x.png",
        "http://[::ffff:127.0.0.1]/x.png",
        "http://0.0.0.0/x.png",
    ],
)
async def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        await assert_public_http_url(url)


async def test_accepts_public_ip_literal() -> None:
    await assert_public_http_url("https://93.184.216.34/x.png")


async def test_unresolvable_host_rejected() -> None:
    with pytest.raises(UnsafeURLError, match="resolved"):
        await assert_public_http_url("https://does-not-exist.invalid/x.png")
