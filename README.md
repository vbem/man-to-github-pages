# man-to-github-pages
Convert man pages to HTML on github pages

[Live Demo](https://vbem.github.io/man-to-github-pages)

### Snapshot
![snapshot](https://raw.githubusercontent.com/vbem/man-to-github-pages/gh-pages/img/snapshot.png)

### Usage
```sh
# checkon github pages branch
git checkout gh-pages

# remove all old man pages' HTML flies
sh clean.sh

# build all man pages on your host into HTML flies
sh build.sh

# ask git to track all new HTML files
sh track.sh

# commit to repo
git commit -m 'renew my man pages today'

# push to your github pages
git push
```

### Q&A
- Q: Aren't http://linux.die.net/man/ and http://man7.org/linux/man-pages/index.html enough for me?
- A: Online man pages services always bind to specific commands and their versions. This project is useful for your own machine's man pages.
