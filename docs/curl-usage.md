# Tips on operating with the system using curl
Since we have not built a dedicated client, here are assorted spells for
interfacing with it through `curl`.



To note for future: As server URLs for testing environment are chosen and the
port the servers listen on is picked, update the spells to be easier to
copy-and-paste.

## Uploading files
To upload a file, the following syntax should provide desired results:
```bash
curl -F "name=<desired filename>" -F "file=@<filepath>" <server-URL:server-port>
```

## Downloading files
To download files, an approach what we can do is
```bash
curl -O http://<server-url:server-port>/<filename>
```
