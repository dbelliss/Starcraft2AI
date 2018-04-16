# Documentations
[C++ Starcraft2 API](https://github.com/Blizzard/s2client-api)
[Starcraft 2 Deepmind API](https://github.com/deepmind/pysc2)
[Python Starcraft2 API](https://github.com/Dentosal/python-sc2)

# How to make a new branch
If you want to create a new branch, you can do so by doing the following.
First we want to check that we are on the master branch
```sh
$ git status
On branch master
Your branch is up-to-date with 'origin/master'.
```
If it states that you aren't on master, then switch to master.
Then we want to check out our new branch.
```sh
$ git checkout -b branch-name-goes-here
```
This should create a local branch for you.
When making a branch name, please follow the following convention:

| Purpose | Branch name |
| ------- | ----------- |
| Fix | fix/*your-short-branch-name* |
| New Feature | feature/*your-short-branch-name* |
| Documentation changes | docs/*your-short-branch-name* |


# Basic Git Workflow
1. Clone the rwpository
```
dbelliss$ git clone https://github.com/dbelliss/Starcraft2AI.git
Cloning into 'Starcraft2AI'...
remote: Counting objects: 5, done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 5 (delta 0), reused 0 (delta 0), pack-reused 0
Unpacking objects: 100% (5/5), done.
dbelliss$ cd Starcraft2AI
```
2. Create a new branch for your feature/fix/documentation
``` sh
dbelliss$ git checkout -b features/test_branch
Switched to a new branch 'features/test_branch'
dbelliss$ 
```
3. Make changes
4. Check what you changed
``` sh
dbelliss$ touch testFile.txt
dbelliss$ git status
On branch features/test_branch
Untracked files:
  (use "git add <file>..." to include in what will be committed)

	testFile.txt
  
nothing added to commit but untracked files present (use "git add" to track)
```
5. Stage your changes for a commit
``` sh
dbelliss$ git add testFile.txt 
dbelliss$ git status
On branch features/test_branch
Changes to be committed:
  (use "git reset HEAD <file>..." to unstage)

	new file:   testFile.txt

dbelliss$ 

```
6. Commit your changes
``` sh
dbelliss$ git commit -m "Adding testFile that documents how to create a Starcraft AI"
[features/test_branch e4c8683] Adding testFile that documents how to create a Starcraft AI
 1 file changed, 0 insertions(+), 0 deletions(-)
 create mode 100644 testFile.txt
dbelliss$ 
```
7. Now, you have only committed your changes on your local repository. You will want to push your changes onto the github with git push. You may need to create the branch on the GitHub if it does not exist
``` sh
dbelliss$ git push
fatal: The current branch features/test_branch has no upstream branch.
To push the current branch and set the remote as upstream, use

    git push --set-upstream origin features/test_branch

dbelliss$ git push --set-upstream origin features/test_branch
Counting objects: 3, done.
Delta compression using up to 4 threads.
Compressing objects: 100% (2/2), done.
Writing objects: 100% (3/3), 314 bytes | 314.00 KiB/s, done.
Total 3 (delta 1), reused 0 (delta 0)
remote: Resolving deltas: 100% (1/1), completed with 1 local object.
To https://github.com/dbelliss/Starcraft2AI.git
 * [new branch]      features/test_branch -> features/test_branch
Branch 'features/test_branch' set up to track remote branch 'features/test_branch' from 'origin'.
dbelliss$ 
```
8. Make sure your push worked by checking the [network graph](https://github.com/dbelliss/Starcraft2AI/network)

# How to make a merge request
Once you are done with your branch and it's ready to be merged into master, make sure that you have no merge conflicts.

Then you can go to our [github repo's branches](https://github.com/dbelliss/Starcraft2AI/branches), and pressing "New pull request" button. You will be brought to this screen. Here you can type out a name and a description for your merge request. Also **assign someone to review your changes**, and notify them via discord or other way that they have a merge request to look over. So we can all keep track of code quality and what gets merged into master.

# How to review a merge request
If you are chosen to review a merge request, please review the changes that the merge request is proposing. If the code looks good, all conventions are followed, no bugs are visible, and no merge conflicts are present, then you can go to step 2.
For step 2, you can approve merge request that:
1. Do not have merge conflicts
2. Code passes the compilation test (Check out the branch yourself and compile it)

If all looks good, you can press "Squash and merge".
![](https://i.imgur.com/Na3ZELm.png)

# How to report an issue
To be organized, we should track all our project issues in one place. Thus, to report an issue go to [issues section on our repo](https://github.com/dbelliss/Starcraft2AI/issues).
Here you can press "New issue" to create a new issue. Fill out a title for the issue, and in the description be as detailed as possible to recreate the issue and explain what the issue is. There will be a template for you to follow.
Here's a sample issue that I created:
![](https://i.imgur.com/1ipbFPw.png)

# Credits
* Made by antonpup for ECS160WindowsTeam

* Modified by dbelliss for Starcraft2AI
