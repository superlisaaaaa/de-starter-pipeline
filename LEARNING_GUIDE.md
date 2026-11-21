# Learning Git, GitHub and CI/CD: a step-by-step guide

This guide assumes you have **never used Git or CI/CD before**. You already
know SQL, Python and Databricks, so we use those as anchors.

Plan for about **6–8 sessions of 1–2 hours**. Do one lesson per session, and don't rush.
Type every command yourself rather than copy-pasting; that's how it sticks.

---

## Part 0: The big ideas in plain words

### What is Git?

Git is a **time machine for a folder of code**.

- Every time you reach a good point, you take a **snapshot**, called a **commit**.
  Each commit has a message ("Add customer dimension") and an ID.
- You can always see what changed, who changed it and why, and go back.
- You've probably seen version history in Databricks notebooks. Git is the
  same idea, but for a *whole project at once*, and it's the industry standard.

### What is a branch?

A **branch** is a parallel copy of the project where you can try something
without touching the working version.

```
main      ●───●───●─────────────●   (the version everyone trusts)
               \               /
my-feature      ●───●───●────●      (your experiment)
```

When your change is ready, you **merge** the branch back into `main`.

### What is GitHub?

Git runs on your laptop. **GitHub** is a website that stores a copy of your
project (a **remote repository**, or "repo") so that:

- your work is backed up,
- teammates can see and review it,
- robots (CI/CD) can run on it.

`git push` sends your commits to GitHub. `git pull` brings other people's commits to you.

### What is a pull request (PR)?

A **PR** is a request: *"Please merge my branch into main."* On GitHub, a PR shows
exactly which lines changed. Colleagues comment and approve it, and **CI runs automatically**.
Nothing reaches `main` without going through a PR. That's how teams keep production safe.

### What is CI (Continuous Integration)?

**CI is a robot that tests every PR.** On each PR, GitHub starts a fresh
Linux machine, installs your project and runs your checks:

1. Is the SQL written in our agreed style? (**lint**)
2. Does the Python logic work? (**unit tests**)
3. Does the pipeline run, and does the data pass its quality rules? (**data tests**)

Green ✅ = safe to merge. Red ❌ = fix first. CI catches mistakes **before**
they reach the dashboards people open every morning.

### What is CD (Continuous Delivery / Deployment)?

**CD is a robot that ships `main`.** When a PR is merged, CD runs the real
pipeline and publishes the result automatically. No one runs scripts by hand,
and no one forgets a step. It can also run **on a schedule** (like a Databricks Job
or Airflow DAG).

### How it all fits together

```
 you                 GitHub                       robots
 ───                 ──────                       ──────
 create branch
 write code
 commit + push  ──►  open pull request  ──────►  CI: lint, tests, dbt build
                     teammate reviews  ◄──────   ✅ / ❌ on the PR
                     merge to main  ─────────►   CD: run pipeline, publish docs
```

---

## Part 1: One-time setup (about 45 minutes)

You'll install four things. Steps are given for **Mac** and **Windows**.

### 1.1 Create a GitHub account

Go to github.com and sign up (free). Use a professional username, because you
might show this repo to employers.

### 1.2 Install Git

- **Mac:** open *Terminal* and type `git --version`. If Git isn't installed,
  macOS offers to install it. Click *Install*.
- **Windows:** download *Git for Windows* from git-scm.com and keep all the defaults.
  This also gives you **Git Bash**, a terminal where every command in this guide works.

Then tell Git who you are (this is written into every commit):

```bash
git config --global user.name "Lisa Wang"
git config --global user.email "the-email-you-used-for-github"
git config --global init.defaultBranch main
```

### 1.3 Install the GitHub CLI (`gh`)

This is the easiest way to sign in to GitHub from the terminal.

- **Mac:** install Homebrew (brew.sh) if you don't have it, then `brew install gh`
- **Windows:** download the installer from cli.github.com

Then sign in. It opens your browser, where you approve it yourself:

```bash
gh auth login
```

Choose: *GitHub.com* → *HTTPS* → *Yes, authenticate Git* → *Login with a web browser*.

### 1.4 Install Python 3.12 and VS Code

- **Python:** python.org/downloads (on Windows, tick **"Add Python to PATH"**).
- **VS Code:** code.visualstudio.com. Its built-in *Source Control* panel
  shows Git visually, which is a great companion to the terminal.

**Check:** `git --version`, `gh --version` and `python --version` (or `python3 --version` on Mac)
each print a version number.

---

## Lesson 1: Run the project on your laptop

Unzip the project somewhere easy, for example `Documents/de-starter-pipeline`.
Open that folder in VS Code, then open its terminal (*Terminal → New Terminal*).

```bash
# 1. Create an isolated Python environment for this project
python -m venv .venv
source .venv/bin/activate        # Windows (Git Bash): source .venv/Scripts/activate
                                 # Windows (PowerShell): .venv\Scripts\activate

# 2. Install exact package versions
pip install -r requirements.txt

# 3. Load the raw files into the bronze layer
python -m pipeline.extract_load
```

You should see one line per file, for example `meter_readings batch=2026-10-02 rows_in_file=16 new_rows=15`.

**Question:** the batch-2 file had 16 rows but only 15 were new. Why?
(Open `scripts/generate_sample_data.py` and look for "duplicate".)

Now **run the same command again.** Every `new_rows` is now `0`. This is
**idempotency**: running a job twice gives the same result as running it once.
In real life, jobs crash and get re-run all the time. If a re-run duplicates data,
every number on every dashboard is wrong. Look at `load_file()` in
`pipeline/extract_load.py` to see how the **row hash + `ON CONFLICT DO NOTHING`**
achieves this. It's the same idea as the MERGE with a hash key you've built in Databricks.

```bash
# 4. Build and test silver + gold with dbt
cd dbt_project
dbt build --profiles-dir .
cd ..

# 5. Run the Python unit tests
pytest -v
```

`dbt build` should end with `PASS=22`. Read these files, in this order:

1. `models/staging/stg_customers.sql`: keeps the **latest version** of each customer (customer C002 changed email in batch 2).
2. `models/staging/stg_meter_readings.sql`: **flags** the negative reading instead of deleting it silently.
3. `models/marts/fct_daily_consumption.sql`: an **incremental** model that only processes new days.
4. `models/staging/_staging.yml`: the **data tests** (unique, not_null, accepted_values, relationships).

Want to look at the data? Run:

```bash
python -c "import duckdb; print(duckdb.connect('warehouse.duckdb').sql('select * from gold.mart_consumption_by_country'))"
```

✅ **You've finished Lesson 1 when** the pipeline, dbt build and pytest all pass on your laptop.

---

## Lesson 2: Your first repository and commit

```bash
# Make sure you're in the project folder (not dbt_project)
git init                     # turn this folder into a Git repository
git status                   # what does Git see?
```

`git status` lists "untracked" files. Notice that `warehouse.duckdb` and `.venv`
are **not** listed. That's because of `.gitignore`. Open it: we never commit generated files,
the database or secrets.

```bash
git add .                    # stage everything (choose what goes in the snapshot)
git status                   # files are now green = staged
git commit -m "Initial commit: starter pipeline"
git log --oneline            # see your history: one commit
```

**Staging vs committing:** `git add` puts files in the "photo frame", and `git commit`
takes the photo. That lets you commit only some of your changes when you want to.

Now put it on GitHub:

```bash
gh repo create de-starter-pipeline --public --source=. --push
```

Open github.com/<your-username>/de-starter-pipeline. Your code is there!

> **Public or private?** Public is needed for free GitHub Pages (Lesson 5), and it lets
> employers see your work. Everything in this repo is fictional, so public is safe.
> Never put company code or real data in a personal repo.

Click the **Actions** tab. CD probably ran already, because you pushed to `main`.
Its "Publish docs" step fails until you finish Lesson 5. That's expected.

✅ **You've finished Lesson 2 when** your code is on GitHub and `git log` shows one commit.

---

## Lesson 3: Branch → pull request → CI

This is **the workflow you'll use every day as a data engineer.**

### 3.1 Create a branch

```bash
git switch -c add-product-mart      # create AND move to a new branch
git branch                          # the * shows where you are
```

### 3.2 Make a change

Create `dbt_project/models/marts/mart_consumption_by_product.sql`:

```sql
-- kWh by product type: which contracts use the most energy?
select
    c.product,
    count(distinct f.contract_id) as contracts,
    round(sum(f.kwh), 1) as total_kwh
from {{ ref('fct_daily_consumption') }} as f
inner join {{ ref('dim_customers') }} as c
    on f.contract_id = c.contract_id
group by c.product
```

Test it locally **before** pushing (always do this):

```bash
sqlfluff lint dbt_project/models
cd dbt_project && dbt build --profiles-dir . && cd ..
```

### 3.3 Commit and push the branch

```bash
git status
git add dbt_project/models/marts/mart_consumption_by_product.sql
git commit -m "Add consumption by product mart"
git push -u origin add-product-mart     # -u: remember where this branch lives on GitHub
```

### 3.4 Open a pull request

```bash
gh pr create --fill
```

(Or on GitHub, click the yellow **"Compare & pull request"** button.) Notice the
description is pre-filled from `.github/pull_request_template.md`.

### 3.5 Watch CI

Open the PR on GitHub and scroll down. You'll see **CI** running. Click **Details**
to watch each step live: install → lint → pytest → load → load again → dbt build.
After about 2 minutes, you should see ✅.

Now open `.github/workflows/ci.yml` and read it top to bottom. Every line has a comment.
Notice:

- `on: pull_request` decides *when* CI runs.
- `runs-on: ubuntu-latest` means a fresh machine every time, so "it works on my laptop" isn't enough.
- `needs: lint-and-unit-test` means stage 2 only runs if stage 1 passed.
- `DUCKDB_PATH` is set by an environment variable, so CI uses its own throw-away database.

### 3.6 Merge

On the PR, click **Merge pull request** → **Confirm**. Then bring `main` up to date on your laptop:

```bash
git switch main
git pull
git log --oneline                # your merged commit is now on main
git branch -d add-product-mart   # tidy up the old branch
```

✅ **You've finished Lesson 3 when** your PR shows a green CI check and is merged.

---

## Lesson 4: Break CI on purpose (the most useful lesson)

You learn CI by watching it **catch mistakes**. Do these one at a time, each on
its own branch: break it → push → watch it go red → fix it → push → watch it go green.

```bash
git switch -c practice-breaking-ci
```

### 4a. Break the SQL style

In `mart_consumption_by_product.sql`, write `SELECT` in capitals and make one line very long.
Commit, push and open a PR. The **"Check SQL style"** step fails.
Read the error: it tells you the file, line and rule. Fix it, commit and push again, and the check turns green.

Tip: `sqlfluff fix dbt_project/models` auto-fixes most style problems.

### 4b. Break the Python logic

In `pipeline/extract_load.py`, change `compute_row_hash` so it ignores the
separator, joining with `""` instead of `"\x1f"`. Push. **pytest** fails on
`test_row_hash_avoids_concatenation_collisions`. That test exists precisely to catch
this subtle bug. Undo the change.

### 4c. Break the data

In `stg_meter_readings.sql`, change `kwh >= 0 as is_valid` to `true as is_valid`.
Push. Lint and pytest pass, but **dbt build** fails on
`assert_no_negative_consumption`: a negative reading would have reached the gold layer.
This is the most important kind of test for a data engineer, because the code "works" but the data is wrong.

### 4d. Break the schema

In `data/landing/2026-10-02/meter_readings.csv`, rename the header `kwh` to `kWh_value`.
Push. The **load step** fails with `SchemaError: missing=['kwh']`, and because of
the transaction, nothing from that batch is half-loaded. Undo the change.

When you're done, close the practice PR without merging, and delete the branch:

```bash
git switch main
git branch -D practice-breaking-ci
```

✅ **You've finished Lesson 4 when** you've seen all four failures and can explain which layer caught each one.

---

## Lesson 5: CD, shipping automatically

### 5.1 Turn on GitHub Pages (one time)

In your repo, go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.

### 5.2 Run CD

Go to **Actions → CD → Run workflow** (or merge any PR). When it finishes:

- The **deploy-docs** job shows a link. Open it: it's your **dbt documentation site**,
  with every model, column and test. Click the lineage graph icon (bottom right) to see
  bronze → silver → gold.
- In the run summary, under **Artifacts**, download `warehouse` (the built database).

### 5.3 Read `cd.yml`

Notice:

- `on: push: branches: [main]` means it ships every merge.
- `schedule: cron: "17 5 * * *"` means it also runs **every day at 05:17 UTC**, like a scheduled Databricks Job.
  Cron format: `minute hour day month weekday`.
- `concurrency` means two deployments never run at the same time.
- `permissions` gives the job **only** the rights it needs (the "least privilege" principle).

> **Real-world version:** instead of a DuckDB file, CD would connect to Snowflake,
> Databricks or BigQuery. The password or token would be stored in
> **Settings → Secrets and variables → Actions** and read as `${{ secrets.SNOWFLAKE_PASSWORD }}`,
> never written in the code.

✅ **You've finished Lesson 5 when** your dbt docs site is live and you can explain what triggers CD.

---

## Lesson 6: Merge conflicts (don't fear them)

A **conflict** happens when two branches change the same line differently. Git can't
guess which one is right, so it asks you.

```bash
git switch -c conflict-a
# in models/marts/mart_consumption_by_country.sql change  round(sum(f.kwh), 1)  to  round(sum(f.kwh), 0)
git commit -am "Round totals to whole kWh"
git switch main
git switch -c conflict-b
# change the SAME line to  round(sum(f.kwh), 2)
git commit -am "Round totals to 2 decimals"
git switch main
git merge conflict-a          # works
git merge conflict-b          # CONFLICT!
```

Open the file. Git marked the clash:

```
<<<<<<< HEAD
    round(sum(f.kwh), 0) as total_kwh,
=======
    round(sum(f.kwh), 2) as total_kwh,
>>>>>>> conflict-b
```

Keep the line you want and delete the markers. (VS Code shows buttons for this:
*Accept Current / Incoming / Both*.) Then:

```bash
git add dbt_project/models/marts/mart_consumption_by_country.sql
git commit -m "Resolve rounding conflict between conflict-a and conflict-b"
```

✅ **You've finished Lesson 6 when** you've resolved a conflict yourself. Then `git push`, or reset with `git reset --hard origin/main` to throw the practice away.

---

## Lesson 7: The data-engineering principles in this project

Re-read the code with this table next to you. These are the ideas interviewers test.

| Principle | What it means | Where to see it |
|---|---|---|
| **Medallion layers** | Raw (bronze) → cleaned (silver) → business-ready (gold) | `pipeline/`, `models/staging`, `models/marts` |
| **Idempotency** | Re-running a job never duplicates or corrupts data | Row hash + `ON CONFLICT DO NOTHING` in `extract_load.py` |
| **Fail fast on schema drift** | Stop loudly if a source changes its columns | `validate_columns()` |
| **Atomic loads** | A batch loads completely or not at all | `BEGIN / COMMIT / ROLLBACK` in `run()` |
| **Audit columns** | Know where every row came from and when | `_batch_id`, `_source_file`, `_loaded_at`, `_load_log` |
| **Keep raw data raw** | Store exactly what you received; clean later | All bronze columns are text |
| **Deduplication / latest version** | One trusted row per entity | `stg_customers`, `stg_meter_readings` |
| **Flag, don't hide** | Mark bad data and keep it countable | `is_valid` in `stg_meter_readings` |
| **Incremental processing** | Only process what's new (with a look-back window) | `fct_daily_consumption.sql` |
| **Data tests** | Rules the data must follow, checked on every run | `_staging.yml`, `_marts.yml`, `tests/` |
| **Unit tests** | Check the Python logic in isolation | `tests/test_extract_load.py` |
| **Config, not hard-coding** | Paths and secrets come from environment variables | `pipeline/config.py`, `profiles.yml` |
| **Reproducibility** | Pinned versions; same result on any machine | `requirements.txt` |
| **Version control + review** | Every change is a reviewed PR | Lessons 2–3 |
| **CI** | Automatic checks before merge | `.github/workflows/ci.yml` |
| **CD + scheduling** | Automatic, repeatable deployment and daily runs | `.github/workflows/cd.yml` |
| **Least privilege** | Jobs get only the permissions they need | `permissions:` in `cd.yml` |
| **Documentation as code** | Docs are generated from the code, so they don't go stale | dbt docs site (Lesson 5) |

---

## Challenges: level up when you're ready

Do each as a branch + PR, so CI checks your work.

1. **Easy:** add a `description` to every column in `_marts.yml`, then look at the docs site.
2. **Easy:** add an `accepted_values` test on `product` in `stg_contracts`.
3. **Medium:** add a third batch folder `data/landing/2026-10-03/` with new readings, and watch the incremental model pick up only new days. (Tip: run `dbt build` twice and compare row counts.)
4. **Medium:** add a test to `tests/test_extract_load.py` proving a missing file raises `FileNotFoundError`.
5. **Medium:** add a gold model with a **data-quality report**: invalid readings per contract per day.
6. **Harder:** turn `stg_customers` into a proper history table with dbt **snapshots** (SCD type 2), so you keep every email the customer ever had, with valid-from/valid-to dates.
7. **Harder:** add a CI step that fails if the gold table has fewer rows than yesterday (a "volume anomaly" check), like the alarm flags in a KPI monitoring framework.
8. **Stretch:** replace DuckDB with a free BigQuery sandbox or Snowflake trial, storing credentials in GitHub Secrets.

---

## Git cheat sheet

| I want to… | Command |
|---|---|
| See what changed | `git status`, `git diff` |
| Stage a file / everything | `git add <file>` / `git add .` |
| Commit | `git commit -m "message"` |
| See history | `git log --oneline --graph` |
| Create + switch to a branch | `git switch -c <name>` |
| Switch branch | `git switch <name>` |
| Send commits to GitHub | `git push` (first time: `git push -u origin <branch>`) |
| Get the latest from GitHub | `git pull` |
| Open a PR | `gh pr create --fill` |
| Check PR / CI status | `gh pr checks` |
| Undo changes to a file (not committed yet) | `git restore <file>` |
| Unstage a file | `git restore --staged <file>` |
| Fix the last commit message | `git commit --amend -m "new message"` |
| Throw away all local work and match GitHub | `git reset --hard origin/main` (careful!) |

**Good commit messages** start with a verb and say *why*:
"Add product mart for pricing team", not "update" or "fix stuff".

---

## How to talk about this in interviews and on your CV

Once you've done Lessons 1–5 and a couple of challenges, you can honestly say:

> *"I built a small end-to-end pipeline on GitHub with a medallion structure in Python and dbt,
> idempotent loads, data tests, and GitHub Actions CI/CD that lints SQL, runs unit and data
> tests on every pull request, and deploys docs on merge."*

And link the repo. That shows hands-on Git, CI/CD and dbt, the three gaps that appear most
often in the analytics engineer and data engineer ads you've been reading.
