class Encoder:
    def encode(self, value):
        if isinstance(value, bytes):
            return str(len(value)).encode() + b':' + value
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            return str(len(encoded)).encode() + b':' + encoded
        elif isinstance(value, int):
            return b'i' + str(value).encode() + b'e'
        elif isinstance(value, list):
            return b'l' + b''.join(self.encode(item) for item in value) + b'e'
        elif isinstance(value, dict):
            result = b'd'
            for key in sorted(value.keys()):
                result += self.encode(key) + self.encode(value[key])
            result += b'e'
            return result
        else:
            raise TypeError(f"Unencodable type: {type(value)}")