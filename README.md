# CS 1 — Intro to Computer Programming

Lecture notebooks for the course. Each lecture is a Jupyter notebook you can
**read, run, and watch as a slideshow**.

```
notebooks/lecture-01-week-1-first-lecture-history-of-computing-introduction-to-co.ipynb
notebooks/lecture-02-week-1-lecture-2-functions-print-variables-input-format.ipynb
…
notebooks/lecture-13-week-12-lecture-13-python-object-oriented-programming.ipynb
```

---

## 1. Getting started

### Step 1 — fork this repository

Click **Fork** in the top-right of this page to create your own copy under your
GitHub account. Work in **your fork**, not in the course repository.

Forking means your notes, edits, and experiments are yours: nothing you do can
affect your classmates or the original material, and you can always compare
against the course copy.

### Step 2 — open a codespace on your fork

From your fork, click **Code → Codespaces → Create codespace on main**.

The codespace installs everything for you — Python, JupyterLab, and the
libraries the lectures use. **You never need to install anything or run a `pip`
command.**

When the codespace first loads, **please don't click anything** — let the
terminal finish its setup on its own. The first build can take close to ten
minutes. You only pay that once: after the codespace exists, reopening it is
quick.

When it finishes, the terminal prints a box like this (**scroll up** if you
don't see it — later output can push it off the screen):

```
  ┌──────────────────────────────────────────────────────────────┐
     CS 1: Intro to Computer Programming — JupyterLab + RISE
  └──────────────────────────────────────────────────────────────┘

  Open:  https://<your-codespace>-8888.app.github.dev/lab?token=…
```

**Click that link.** JupyterLab opens in a new browser tab. Open any lecture
from the `notebooks/` folder in the file browser on the left.

> **Lost the link?** Run this in the terminal:
>
> ```bash
> bash .devcontainer/start-jupyter.sh
> ```
>
> Add a lecture number to have the link open that lecture directly, instead of
> leaving you in the file browser:
>
> ```bash
> bash .devcontainer/start-jupyter.sh 12
> ```
>
> You can also find the server under the **Ports** tab (port 8888) — but use the
> printed link if you can, because it carries the `?token=…` the server needs.

> **The link must start with `https://` and end with `?token=…`.** If you are
> looking at a `http://127.0.0.1:8888` or `http://codespaces-…:8888` address,
> that is the address *inside* the container and your browser cannot reach it.
> Re-run the command above to get the real one.

---

## 2. Turning a lecture into a slideshow

### Step 1 — press `Esc`

This puts the notebook in *command mode*. If your cursor is blinking inside a
code cell, keyboard shortcuts get typed into the cell instead of running.

### Step 2 — press `Option` + `R`  &nbsp;(Windows/Linux: `Alt` + `R`)

The slideshow opens in a panel beside the notebook. Use the **⛶ fullscreen
button** in that panel's toolbar to fill the screen.

To close it, click the **×** on the slideshow panel's tab.

---

## 3. Moving around a slideshow

A deck is one straight sequence. There is no second direction to learn.

| Key | What it does |
| --- | --- |
| `→` / `←` | Move **forward / back one slide** |
| `Space` / `Shift`+`Space` | Exactly the same thing, if you prefer a bigger key |

```
→   →   →   →   →   →
[1] [2] [3] [4] [5] [6]  …
```

That includes live examples: a 📈 `LIVE EXAMPLE` banner is followed by its steps
as ordinary slides, one per press, each showing its explanation and the code it
describes together.

If a slide has more content than fits on screen, just **scroll** — the slide
scrolls on its own.

### Running code during a lecture

Many slides hold real, runnable Python. Every code cell has a **▶ button** at
its top-left — click it to run that cell.

If you prefer the keyboard, click into the cell and use:

| Key | What it does |
| --- | --- |
| `Shift`+`Enter` | Run the cell and **stay on the current slide** |
| `Ctrl`+`Enter` or `Cmd`+`Enter` | Same thing |

The button pulses while the cell is running and returns to normal when it
finishes. Nothing here advances the slide — you move with `Space` or `→`.

**Cells that ask you a question.** A lot of these lectures use `input()`, so a
cell will stop and wait for you to type an answer. Click in the box, type, and
press `Enter`. While a cell is waiting, its ▶ button becomes a red ■ **stop**
button — click that if you'd rather abandon it than answer. You can also just
run a different cell; the waiting one is stopped for you automatically.

Edit the code and re-run it as much as you like; it's your own copy and
you can't affect anyone else.

---

## 4. What you'll see in a lecture

**Content slides** — the material itself: explanations, diagrams, formulas, and
code you can run.

**Live examples** — a teal banner marked 📈 `LIVE EXAMPLE`, followed by a worked
notebook broken into steps, one per slide. These are meant to be run: press `→`
through them like any other slide.

**In-class exercises** — an amber card marked 🧪 `IN-CLASS EXERCISE`:

```
🧪 IN-CLASS EXERCISE
Exercise: Skiing Weather

Exercise link:  <PrairieLearn URL here>
```

These are **signposts, not the exercise**. The exercise itself lives in PrairieLearn,
don't try to do it inside the notebook.

---

## 5. What you can and can't safely change

**Safe to edit:** the notebooks in `notebooks/`. Change the code, add cells, take
notes, re-run whatever you like. That is what your fork is for.

**Please leave everything else alone.** In particular:

| Don't touch | Why |
| --- | --- |
| `.devcontainer/` | builds your codespace — a bad edit here means it won't start |
| `requirements.txt` | installs Python and the course libraries |
| `tools/` | generates the notebooks and configures the slideshow keys |

Editing those risks breaking your environment, and the failure usually shows up
later as a codespace that won't open or a slideshow that comes up blank. If you
only change files inside `notebooks/`, you can't get into that state.

Nothing is locked, so if you do break something, see the last two entries in
section 6 below.

---

## 6. If something goes wrong

**The slideshow is blank / white.**
Give it a few seconds — a deck takes a moment to build. Also click inside the
browser tab: browsers don't draw tabs you haven't focused yet.

**`Option+R` does nothing.**
Either you're in edit mode (press `Esc` first — see step 1), or you're in the
**VS Code notebook editor** rather than JupyterLab. The slideshow is a
JupyterLab feature; VS Code cannot run it. Editing in VS Code is fine, but
presenting needs the JupyterLab link from the terminal.

**A plot didn't appear.**
Run that example's cells in order from the top — later cells usually depend on
variables defined in earlier ones.

**I broke a notebook.**
`git checkout -- notebooks/` in a terminal restores every lecture to its
original state.

**I edited something outside `notebooks/` and things stopped working.**
`git checkout -- .` restores everything. If the codespace itself is broken, the
quickest fix is to delete it and create a new one — you lose nothing that you
have committed and pushed.

---

## 7. Running on your own machine instead

You don't have to use Codespaces. From a clone of this repository:

```bash
./present.sh          # list the lectures
./present.sh 5        # present lecture 5
```

That opens the lecture straight into the slideshow — you don't need to press
`Alt+R`. It points Jupyter at an isolated `.jupyter-rise/` config directory
rather than your real `~/.jupyter`, so it cannot disturb any other Jupyter setup
on your machine, and it turns off the four extensions listed below for its own
session only. Press `Ctrl+C` in that terminal when you're done.

You need `jupyterlab` and `jupyterlab_rise` installed for it
(`pip install -r requirements.txt`).

If you'd rather run plain `jupyter lab` yourself, one catch: your JupyterLab
**must not** have the `jupyter-widgets`, `pyviz`/`panel`, `plotly`, or
`variableinspector` extensions installed. RISE can't load alongside them and the
slideshow comes up blank. Anaconda installations ship these by default, which is
why both the codespace and `present.sh` use a clean environment instead. If
you're on Anaconda and hit a blank slideshow, use `present.sh` or the codespace.

---
