

# Gemini Agent

This project is built using Google’s Gemini API to interact with your system and take care of a bunch of tasks for you.

Originally, I made it to help me out with my **Database Systems 3** module (read: I was too lazy to do everything manually). But it turned into something more general. The model has a few tools baked in to make life easier:

* **Database management** – mostly so I don’t have to do it myself.
* **File read/write** – great for when you're coding and need some help (basically a poor man’s GitHub Copilot).
* **URL context scraping** – just text for now, but handy when you want the model to read updated docs for some library or error you're stuck on.

---

### Memory (or why it's kinda slow)

One annoying thing: Gemini doesn’t support memory out of the box. So, it can’t naturally remember your preferences or personality. To hack around that, I made a custom internal function that kicks in whenever you mention something about yourself. Example:

```
You: I like Python
```

Gets stored in ChromaDB as:

```
User prefers Python language
```

So later on, if you ask something like “what language should I use for X?”, the model will already know you lean Python and tailor its response accordingly.

This setup works, but yeah—it’s slower because I have to manually load the saved memory each time. Planning to optimize that eventually (when I feel like it).

---

### Config Stuff

All model configs live in the `configs` directory. If you want to:

* Switch the model being used
* Change how many tokens it spits out
* Set a custom path for your ChromaDB storage

…you’ll find all that there. By default, ChromaDB saves in the parent directory and is Git-ignored (because it can blow past 50MB real quick).

---

That’s about it. Built this mainly for myself, but if it helps you too—cool.
 
