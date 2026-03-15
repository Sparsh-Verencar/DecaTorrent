import hashlib

class Decoder:
    def __init__(self):
        self.raw_content = None
        self.info_hash = None

    def decode(self, file):
        self.raw_content = file.read()
        parsed, _ = self._decode_next(self.raw_content, 0)
        return parsed

    def _decode_next(self, data, i):
        c = chr(data[i])
        if c.isdigit():
            return self._decode_string(data, i)
        elif c == 'i':
            return self._decode_int(data, i)
        elif c == 'l':
            return self._decode_list(data, i)
        elif c == 'd':
            return self._decode_dict(data, i)
        else:
            raise ValueError(f"Unexpected token '{c}' at position {i}")

    def _decode_string(self, data, i):
        j = i
        while chr(data[j]).isdigit():
            j += 1
        length = int(data[i:j])
        start = j + 1
        end = start + length
        return data[start:end], end

    def _decode_int(self, data, i):
        end = data.index(ord('e'), i + 1)
        number = int(data[i + 1:end])
        return number, end + 1

    def _decode_list(self, data, i):
        i += 1
        result = []
        while chr(data[i]) != 'e':
            value, i = self._decode_next(data, i)
            result.append(value)
        return result, i + 1

    def _decode_dict(self, data, i):
        i += 1
        result = {}
        while chr(data[i]) != 'e':
            key, i = self._decode_next(data, i)
            if key == b'info':
                info_start = i
                value, i = self._decode_next(data, i)
                info_end = i
                self.info_hash = hashlib.sha1(
                    self.raw_content[info_start:info_end]
                ).digest()
            else:
                value, i = self._decode_next(data, i)
            result[key] = value
        return result, i + 1