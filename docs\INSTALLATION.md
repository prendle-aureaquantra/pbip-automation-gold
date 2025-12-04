# Installation Guide - Gold Tier

## Prerequisites

- Python 3.8 or higher
- Power BI Desktop (free)
- Git (for version control)

## Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/prendle-aureaquantra/pbip-automation-gold.git
   cd pbip-automation-gold
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your license key:**
   - Copy your license key from the email
   - Paste it into `LICENSE_KEY.txt`
   - Or set as environment variable: `export PBIP_LICENSE_KEY=your-key`

4. **Verify installation:**
   ```bash
   python generate_pbip.py --help
   ```

## Next Steps

- See `docs/USAGE.md` for usage examples
- Check `templates/` for available templates
- Review `examples/` for sample projects
