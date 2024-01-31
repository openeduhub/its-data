#!/bin/sh
git checkout gh-pages
git fetch origin
git rebase origin/main
nix build .\#docs --out-link docs-result &&
    cp -rf $(readlink -f docs-result)/* docs &&
    rm docs-result &&
    chmod -R +r docs
