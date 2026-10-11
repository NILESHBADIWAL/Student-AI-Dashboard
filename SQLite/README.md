# Classical Cipher Socket Demonstration

This learning project implements three **symmetric-key classical ciphers** and sends the resulting ciphertext from a client (source node) to a server (destination node).

Available ciphers:

1. **Caesar cipher** — a shift from 1 to 25.
2. **Monoalphabetic substitution cipher** — a 26-letter permutation key, such as `QWERTYUIOPASDFGHJKLZXCVBNM`.
3. **Columnar transposition cipher** — a keyword with no repeated letters, such as `ZEBRAS`.

Both implementations use the same simple wire format:

```
cipher_name|key|ciphertext\n
```

The server prints the received ciphertext and decrypts it to prove that the same symmetric key recovers the original message.

> **Important security note:** Caesar, monoalphabetic substitution, and transposition ciphers are easy to break. They are appropriate only for learning cryptography and socket programming. They do **not** securely transmit sensitive data. Also, this demo sends the key with the message so the server can demonstrate automatic decryption; that is deliberately insecure. In a real system use TLS plus authenticated modern encryption such as AES-GCM, and do not send the secret key with the ciphertext.

## Python

Open two terminals in this folder.

```powershell
python python/server.py
python python/client.py
```

The client asks which cipher to use, asks for its key, encrypts the plaintext locally, and sends only the encrypted message record. The server shows what it received and the recovered plaintext.

## C++ (Windows / Winsock)

Compile in two terminals or compile both before running. With MinGW g++:

```powershell
g++ -std=c++17 cpp/server.cpp -o cpp/server.exe -lws2_32
g++ -std=c++17 cpp/client.cpp -o cpp/client.exe -lws2_32
```

Run in separate terminals:

```powershell
.\cpp\server.exe
.\cpp\client.exe
```

For Microsoft Visual C++, the `#pragma comment(lib, "Ws2_32.lib")` directive already links Winsock.

## Try it

Start the server first. On the client choose, for example:

- Caesar: plaintext `Meet at 5 PM`, key `3`
- Monoalphabetic: plaintext `Meet at 5 PM`, key `QWERTYUIOPASDFGHJKLZXCVBNM`
- Transposition: plaintext `Meet at 5 PM`, key `ZEBRAS`

For different machines, replace `127.0.0.1` in the client source with the destination server's LAN address, permit TCP port 5000 through the server firewall, and keep both endpoints on a network you control.
