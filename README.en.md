# CFIRE Agent Skills

A reusable collection of virtual artist operation agent skills. Provides a complete skill system from artist profile management, daily operations, content publishing, to fan interaction.

## Directory Structure

```
cfire-agent-skills/
├── README.md                # This document
├── config.example.json      # Configuration file example
├── config_loader.py         # Unified configuration loader
├── requirements.txt         # Python dependencies
│
├── cfire-artist-profile/    # Artist profile management skill
│   ├── SKILL.md
│   ├── scripts/             # Persona review and other scripts
│   ├── memory_store/        # SQLite memory storage and retrieval
│   └── reference/           # Profile templates and specifications
│
├── cfire-artist-daily/      # Daily operations skill
│   ├── SKILL.md
│   ├── scripts/             # Diary, content planning scripts
│   └── assets/              # Diary and content planning storage
│       ├── diary/
│       └── content_draft/
│
└── cfire-artist-post/       # Post publishing skill
    ├── SKILL.md
    └── scripts/
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Current dependencies:
- `requests>=2.28.0`: HTTP requests
- `jieba>=0.42.1`: Chinese tokenization (for memory retrieval)

### 2. Configuration

Copy the configuration example file:

```bash
cp config.example.json config.json
```

Then edit `config.json` and fill in your API configuration and artist information. Environment variable configuration is also supported, see below.

### 3. Initialize Artist Profile

Before first use, you need to configure the artist profile in the `cfire-artist-profile/reference/` directory. Refer to the bootstrap process in `BOOTSTRAP.md`, or directly edit `.template` files and remove the suffix.

### 4. Use Skills

Each skill can be used via command line. For detailed instructions, see the `SKILL.md` file in each skill directory.

Examples:

```bash
# Generate diary (requires LLM environment variables)
cd cfire-artist-daily
python scripts/skill.py generate -d 2026-06-26 --save

# Publish a post
cd ../cfire-artist-post
python scripts/skill.py publish -a "Example Artist" -c "Great rehearsal today!"
```

## Skills Overview

### cfire-artist-profile

Artist profile management skill, the foundation of all skills. Core capabilities:
- **Artist Onboarding**: Create a complete artist profile system from scratch through structured Q&A
- **Persona Maintenance**: Read and maintain consistency in artist identity, personality, and expression style
- **Memory Management**: Long-term storage and inverted index retrieval based on SQLite
- **Persona Change Review**: Risk classification and impact assessment for character setting changes
- **Safety Review**: Pre-publication safety and quality checks
- **Learning & Evolution**: Accumulate experience from execution results to optimize future output

### cfire-artist-daily

Daily operations skill, responsible for artist daily content production and timeline management:
- **Diary Management**: Generate, save, and validate daily artist diaries (≤200 characters)
- **Content Planning**: Generate topic planning and shooting scripts (supports short video three-act structure)
- **Timeline Management**: Maintain artist narrative timeline and event records
- **Schedule Management**: Manage artist event arrangements and work plans

### cfire-artist-post

Post publishing skill, calls server-side API through artist-independent API Key authentication:
- Text-only post publishing (10 energy cost)
- Image-text post publishing (50 energy cost)
- Post with external video links (supports Bilibili, YouTube, TikTok, Douyin, Kuaishou)
- Growth Post: Publish in one format first, then add other formats later

## Configuration

### config.json Format

```json
{
  "api_base_url": "https://your-api-domain.com",
  "artists": {
    "Artist Name": {
      "artist_id": "Artist UUID",
      "user_id": "Default operation user UUID",
      "api_key": "Artist API Key"
    }
  }
}
```

### Environment Variables

Configuration can also be done via environment variables:
- `CFIRE_API_BASE_URL`: API base URL
- `CFIRE_ARTIST_{NAME}_API_KEY`: Artist API Key (replace spaces in NAME with underscores)

## Development Guide

### Skill Dependency Graph

```
cfire-artist-profile  (foundation)
    ↑
    ├── cfire-artist-daily
    └── cfire-artist-post
```

- `cfire-artist-profile` is the foundation skill; all other skills depend on it to read artist profiles and memories
- `cfire-artist-daily` additionally depends on `memory_store` for timeline and memory writes

### Adding a New Skill

1. Create a new directory under `cfire-agent-skills/`, named `cfire-artist-xxx`
2. Create a `SKILL.md` document (include name and description in YAML frontmatter)
3. Implement core logic in the `scripts/` directory
4. Use the unified `config_loader.py` to load configuration
5. Follow the same CLI interface style as existing skills
6. Write logs uniformly to `scripts/logs/skill.log`

### Code Standards

- Follow PEP 8 coding standards
- Add necessary type annotations
- Use Chinese comments and docstrings
- Include comprehensive error handling and idempotency design
- Error code handling: Do not blindly retry on 400/401/403/404/409

## Notes

1. **Security**: Never commit `config.json` containing real API Keys to version control
2. **Dependencies**: `cfire-artist-daily` depends on `cfire-artist-profile`, ensure the directory structure is correct
3. **Log Management**: All skills generate log files in their respective `scripts/logs/` directories
4. **Database**: `cfire-artist-profile/memory_store/` will create SQLite database files
5. **Cache Files**: Do not commit `__pycache__/`, `.pyc` files, etc. to version control
6. **Authentication Issues**: When encountering 401 errors, check configuration first - do not modify the code

## License

Please refer to the license file in the project root directory.
