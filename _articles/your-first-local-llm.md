---
title: Your first local LLM
description: "What ‘local’ means, what a model file is, picking one that fits, and the moment it answers you — practiced on a real machine."
section: setup
builds_on: []
next: /mem/
image: /images/your-first-local-llm/hero.png
alt: "A faintly glowing brain in a glass specimen jar, painted in sepia watercolor on dark parchment."
plate_sub: "The off-the-shelf foundation: a language model that runs on the machine in front of you, and nothing behind it."
---

You have used cloud language models. You know what they do. What this article
teaches is what *local* means when the model runs on your own machine, what the
files you download actually are, how to size one to fit your hardware, and how
the context window stops being an abstraction the moment it becomes a number
you can watch.

None of this phones home. Every command here was run on the machine these sites
were written on — a 64 GB Apple Silicon laptop — and the numbers you are shown
are the ones it produced. Your machine is different; the arithmetic is not.

## What “local” means

A local LLM is a model loaded into your own memory, running on your own
hardware, talking to you over your own loopback interface. The practical
consequences, in order:

- **It works where you are.** No subscription, no provider outage, no request
  queue behind someone else’s quota. If it is loaded, it answers.
- **Nothing leaves the machine.** Your prompts go into RAM and come back.
  There is no telemetry path because there is no network path.
- **It costs you two things instead of a subscription.** A download, and part of
  your machine’s memory and thermal budget. Those are the two budgets this
  article is about.

The mental shift the cloud never asked for: a model is not a service, it is a
file in memory. Everything else in this article follows from that.

## The stack: three engines, one habit

This machine runs three runtimes, and it is worth knowing what each one is
before you pick.

**Ollama** is the door. It downloads models, serves them, and exposes an
OpenAI-compatible endpoint on `127.0.0.1:11434`. You will live here most of the
time. On this box the install is one binary (`/usr/local/bin/ollama`, a
universal Mach-O from the official installer), and the service runs resident.

```
$ ollama pull qwen3.5:4b
$ ollama run qwen3.5:4b "Say hello in one sentence."
$ curl http://127.0.0.1:11434/api/tags   # what is installed
$ ollama ps                               # what is loaded, and its context
```

**llama.cpp** is the engine under most of the workhorses. It is the C runtime
that reads GGUF files, and it is what Ollama runs underneath for them. You
usually do not touch it directly; you meet it in the next section, in the file
format it made standard.

**MLX** is Apple’s answer: a tensor framework built for the unified memory of
Apple Silicon, and a matching model family (`mlx-lm`, and Ollama’s MLX runners).
On this box the 27B model loads through Ollama *as an MLX runner* — the `ollama
ps` column is the tell:

```
NAME              SIZE     PROCESSOR   CONTEXT   RUNNER
rosey-27b-256k    32 GB    100% GPU    262144    mlx
```

One model, three names. The point of knowing all three is not to run all three;
it is that when you read a tutorial, you will recognize which layer of the stack
it is talking about.

## Model formats: what the file is

A model is a few to a few hundred gigabytes of trained weights, and the
container format tells you which runtime can read it.

**GGUF** is the workhorse. A C-friendly binary format born in llama.cpp, widely
shared on Hugging Face, and the one Ollama speaks natively. A GGUF filename
carries its resolution: `7B`, `8B`, `27B` is the parameter count; `Q4_K_M`,
`Q8_0` is the quantization. Quantization is compression in the sense that every
weight is stored in fewer bits — the quality-to-size tradeoff you will spend the
next section navigating.

**safetensors** is PyTorch’s container — the native format of most research
models, read by transformers and the Python ecosystem. Larger than the
equivalent GGUF, and for running interactively you will rarely want it; it is
the format that appears when you leave Ollama’s world.

**MLX** is the Apple-Silicon native format. It is built for unified memory,
where the CPU and GPU share one pool, and in practice the same model runs
faster in MLX than in a GGUF port on the same box. Ollama will load MLX models
for you, which is how this site’s 27B lives — the MLX path is reachable through
the door without a second tool.

The practical rule: **start with GGUF via Ollama.** It is the path with the fewest
concepts in it: pull, run, done.

## Choosing a model that fits

The machine question is arithmetic, and it reduces to one line:

> weights, in memory, plus the context you hand it, must fit in RAM.

Weights scale with parameter count and bits per parameter. Two rules of thumb
that survive contact with hardware:

- **The parameter count is the size class.** A `4B` model’s weights are
  a few GB at Q4-K-M; an `8B` model about double that; a `27B` model a
  little over triple.
- **The quant sets the multiplier.** Q8-0 is roughly one byte per parameter.
  Q4-K-M is a little over half a byte — the standard choice, near-identical
  quality at the half price. Q2-class lives on the edge of coherence.

Handed a machine, you read the table, not the marketing:

| model | file on disk | loads on |
| --- | --- | --- |
| 4B, Q-class | ~4 GB | anything modern |
| 9B, Q8_0 | ~10 GB | comfortable |
| 27B, Q-class | ~15 GB | this 64 GB box, all day |

This box is a 64 GB Apple M3. The 27B model holds its ~15 GB of weights, a
262,144-token context, and a Python process the size of a browser — and there is
still room. The rule in one sentence: **halve the machine’s RAM, cover the
weights with one half, spend the other half on context and the rest of your
life.** A 16 GB laptop runs 8B-class with a moderate context, comfortably; the
64 GB box runs 27B-class with the context wide open, and that gap between
comfortable and wide open is most of what “local on a good machine” is worth.

Find out what your machine can hold the way this one found out: pull a size
class you *think* fits, watch `ollama ps`, and read the number. The table above
is what that reading gave us here.

## Context in practice

The cloud hid this from you; on your machine it is a dial.

The model’s memory is two things. The weights — what it *is* — and the **KV
cache** — what it *remembers*, one growing allocation per token you and it have
exchanged. Context is the second thing made visible. Three consequences:

1. **Context is a physical budget.** On this box the 27B model is loaded with a
   262,144-token window. That is not a marketing number: it is an allocation
   plan against 64 GB of RAM, and it shows up as a number in `ollama ps`.
   Double the context and you are asking twice the memory for the same
   conversation.
2. **It does not remember by keeping; it remembers by carrying.** Every turn,
   the entire conversation rides along with the query. That is why a model
   “forgets” after a long session: not decay, just window. When the
   conversation outgrows the window, the oldest tokens fall off the end.
3. **A smaller model with a long context is not a better model.** Attention
   over 100k tokens is a tax a small model pays with quality. Pick the biggest
   model the RAM holds, then give it a context long enough for your work —
   tens of thousands of tokens for real tasks, not the maximum.

The discipline this buys: you can look at the machine and see what a
conversation costs.

## The first turn

Everything above is setup. The moment that matters is the first answer.

```
$ ollama run qwen3.5:4b "In one sentence, what am I running?"
```

The first run of any model takes its time — the weights stream from the network
on the first pull, then load into memory, and the answer arrives. On this box
the 4B model pulls in seconds; a 27B takes minutes and about 15 GB of
discipline. The sentence it gives you will be short and slightly generic. That
is fine. The fact that the sentence was produced by your laptop, using your
electricity, with no one else’s involvement, is the whole event.

After that, the model is a facility you have: a reasoning engine with no
meter. The rest of this site is what we did with the idea.

## What’s next

A model that answers you, and nothing more — it has no memory that survives the
session, and none of its own way to keep track of anything. The first organ was
built to fix exactly that:

**[mem — memory that survives the session](/mem/)**
