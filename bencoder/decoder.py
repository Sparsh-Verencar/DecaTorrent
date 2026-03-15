class Decoder:
    def __init__(self, parsedFilePath):
        self.parsedFilePath = parsedFilePath
    def decode(self, file):
        content = file.read()
        i = 0
        with open(self.parsedFilePath, "w") as t:
            while i < len(content):
                c = content[i]
                if c.isdigit():
                    j = i
                    while content[j].isdigit():
                        j += 1
                    length = int(content[i:j])
                    data = content[j+1 : j+1+length]
                    t.write(f"{data}\n")
                    i = j + 1 + length

                elif c == 'i':
                    end = content.index('e', i)
                    number = int(content[i+1:end])
                    t.write(f"{number}\n")  
                    i = end + 1
                elif c == 'l':
                    i += 1
                    result = []
                    while content[i] != 'e':
                        if content[i].isdigit(): 
                            j = i
                            while content[j].isdigit():
                                j += 1
                            length = int(content[i:j])
                            data = content[j+1 : j+1+length]
                            result.append(data)
                            i = j + 1 + length
                        elif content[i] == 'i':  
                            end = content.index('e', i)
                            number = int(content[i+1:end])
                            result.append(number) 
                            i = end + 1
                    i += 1  
                    t.write(f"{result}\n")
                elif c == 'd':
                    i += 1
                    result = dict()
                    isKey = True
                    key, value = " ", " "
                    while content[i] != 'e':
                        if isKey:
                            if content[i].isdigit(): 
                                j = i
                                while content[j].isdigit():
                                    j += 1
                                length = int(content[i:j])
                                data = content[j+1 : j+1+length]
                                key = data
                                i = j + 1 + length
                                isKey = False
                        else:
                            if content[i].isdigit(): 
                                j = i
                                while content[j].isdigit():
                                    j += 1
                                length = int(content[i:j])
                                data = content[j+1 : j+1+length]
                                value = data
                                i = j + 1 + length
                                result[key] = value
                                isKey = True
                            elif content[i] == 'i':  
                                end = content.index('e', i)
                                number = int(content[i+1:end])
                                value = number 
                                i = end + 1
                                result[key] = value
                                isKey = True
                    i += 1  
                    t.write(f"{result}\n")
                else:
                    i += 1
            