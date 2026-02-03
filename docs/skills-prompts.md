# Skills & Prompts

Skills and prompt templates are loaded on demand to keep context lean while keeping reusable workflows handy.

## Storage
- Skills live in `config/skills/<name>/SKILL.md`
- Prompts live in `config/prompts/<name>.md`
- Both support frontmatter metadata (`name`, `description`, `tags`, etc.).

## Loading rules
- Global and project scopes are supported.
- Resource discovery exposes names and descriptions; content is fetched on explicit request.

## UI behavior
- `/skill <name>` inserts the selected skill template.
- `/prompt <name>` inserts a prompt template.
- Settings allow enabling or disabling individual skills/prompts.

## APIs
- `GET /api/resources`
