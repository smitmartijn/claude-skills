# Claude Code Skills

A collection of skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Each skill is a self-contained `SKILL.md` that teaches Claude how to perform a specific task.

## Available Skills

| Skill | Description |
|-------|-------------|
| [transcribe-video](transcribe-video/) | Transcribe video/audio to plain text using ffmpeg + whisper. Fast on Apple Silicon. |
| [thumbnail-video](thumbnail-video/) | Generate YouTube thumbnail variants with scene detection, HTML/CSS templates, and headless Chrome. |

## Installation

### Install a single skill

```bash
curl -sL https://raw.githubusercontent.com/smitmartijn/claude-skills/main/install.sh | bash -s -- transcribe-video
```

### Install all skills

```bash
curl -sL https://raw.githubusercontent.com/smitmartijn/claude-skills/main/install.sh | bash -s -- --all
```

### Update a skill

Run the same install command again — it overwrites the existing skill files.

### Uninstall a skill

```bash
rm -rf ~/.claude/skills/transcribe-video
```

## Skill structure

Each skill lives in its own directory with a `SKILL.md` file:

```
skill-name/
└── SKILL.md
```

The `SKILL.md` contains YAML frontmatter (`name`, `description`) and the full instructions Claude follows to execute the skill.

## Writing your own skills

Fork this repo and add a new directory with a `SKILL.md`. The frontmatter `description` field is what Claude uses to decide when to trigger the skill, so make it specific about the phrases and intents it should match.

## License

MIT
