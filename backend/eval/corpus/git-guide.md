# Git guide

## Undoing commits

To undo the most recent commit but keep its changes staged, run `git reset --soft HEAD~1`. Use `git revert <sha>` instead on shared branches, because revert adds a new commit that undoes the old one without rewriting history.

## Branches

Create and switch to a new branch with `git switch -c feature/login`. List local branches with `git branch` and delete a merged branch with `git branch -d feature/login`.

## Rebase versus merge

Merging preserves the exact history and adds a merge commit. Rebasing replays your commits on top of another branch to produce a linear history. Never rebase commits that other people have already pulled.

## Stashing

`git stash` shelves uncommitted changes so you can switch tasks with a clean working tree. Bring them back later with `git stash pop`, which reapplies the newest stash and removes it from the stash list.

## Merge conflicts

When two branches change the same lines, Git stops and marks the file with conflict markers: `<<<<<<<`, `=======` and `>>>>>>>`. Edit the file to keep the right content, delete the markers, then `git add` the file and continue.

## Tags

Mark a release with an annotated tag: `git tag -a v1.0 -m "First release"`. Tags are not pushed by default; push them with `git push --tags`.
