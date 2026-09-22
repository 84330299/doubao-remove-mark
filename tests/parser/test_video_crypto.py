import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from parser.video_crypto import decode_main_url, decode_qaab_token

# The salt below is the fixed constant used by Doubao's token derivation.
# It is reproduced here (independent of the module under test) so the tests
# build ciphertext with the real constant, not with whatever the code imports.
QAAB_SALT = bytes.fromhex(
    "4dd4c2e6b83162090e52b3c7a6733ba4"
    "1cb2462b829ab58a196b39db57177524"
    "f49baf7f08e8d68d26a72e37c1a95a2f"
    "1f05a51892aef2949732b62a38aadd58"
)


def _derive_key_iv(key_seed: bytes) -> tuple[bytes, bytes]:
    first_digest = hashlib.sha512(key_seed[:32]).digest()
    material = hashlib.sha512(first_digest + QAAB_SALT).digest()
    return material[:16], material[16:32]


def _aes_cbc_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    block = 16
    pad_len = block - (len(plaintext) % block)
    padded = plaintext + bytes([pad_len]) * pad_len
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode()


class TestPlainHttpUrl:
    def test_returns_http_url_unchanged(self):
        url = "https://v.douyinvod.com/xxxx/stream.mp4"
        assert decode_main_url(url) == url

    def test_returns_https_url_unchanged(self):
        url = "https://example.com/video/play.m3u8"
        assert decode_main_url(url) == url


class TestBase64WrappedUrl:
    def test_decodes_standard_base64_url(self):
        url = "https://www.doubao.com/video/abc123.mp4"
        token = _b64(url.encode())
        assert decode_main_url(token) == url

    def test_uses_first_loose_variant_for_dollar_underscore(self):
        # "&" b64-encodes to Jg== -> the '$' variant maps $ -> _, @ -> /, # -> .
        url = "https://a.com/x&y.mp4"
        raw = base64.b64encode(url.encode()).decode().replace("+", "$").replace("/", "@").replace("=", "#")
        assert decode_main_url(raw) == url

    def test_empty_token_returns_empty(self):
        assert decode_main_url("") == ""

    def test_non_decodable_token_returns_empty(self):
        assert decode_main_url("!!!not base64!!!") == ""


class TestQaabToken:
    def test_decrypts_valid_qaab_token(self):
        url = "https://v3.douyinvod.com/abcdefg/hijklmn.mp4"
        key_seed = "some-random-seed-value-0123456789"
        seed_bytes = key_seed.encode()

        key, iv = _derive_key_iv(seed_bytes)
        ciphertext = _aes_cbc_encrypt(url.encode(), key, iv)
        # The "qAAB" marker *is* the base64 of the 4-byte magic prefix, so the
        # real token is a single base64 blob of magic + ciphertext.
        token = _b64(b"\xa8\x00\x01\x00" + ciphertext)

        assert token.startswith("qAAB")
        assert decode_main_url(token, _b64(seed_bytes)) == url

    def test_qaab_without_key_seed_returns_empty(self):
        url = "https://v3.douyinvod.com/aaaa/mmmm.mp4"
        key_seed = "seed-without-key"
        key, iv = _derive_key_iv(key_seed.encode())
        ciphertext = _aes_cbc_encrypt(url.encode(), key, iv)
        token = _b64(b"\xa8\x00\x01\x00" + ciphertext)
        assert decode_main_url(token) == ""

    def test_decode_qaab_token_accepts_key_seed_as_base64(self):
        # The module base64-decodes key_seed too; feed it base64-wrapped seed.
        url = "https://v3.douyinvod.com/zzzz/qqqq.mp4"
        seed_bytes = b"seed-ascii-bytes-16bytes!"
        key, iv = _derive_key_iv(seed_bytes)
        ciphertext = _aes_cbc_encrypt(url.encode(), key, iv)
        token = _b64(b"\xa8\x00\x01\x00" + ciphertext)
        assert decode_qaab_token(token, _b64(seed_bytes)) == url


def test_qaab_salt_constant_matches_module():
    from parser import video_crypto

    assert video_crypto.QAAB_SALT == QAAB_SALT
