# Usage Guide - Gold Tier

## Basic Usage

### Generate a PBIP from Template

```bash
python generate_pbip.py --template sales-dashboard --output my-dashboard
```

### Generate with Custom Config

```bash
python generate_pbip.py --config my-config.yaml --output my-report
```

## Available Templates

See `templates/` directory for available templates based on your tier.

## Configuration

Create a YAML configuration file:

```yaml
model:
  name: "My Report"
  tables:
    - name: "Sales"
      columns:
        - name: "Date"
          type: "date"
        - name: "Amount"
          type: "decimal"
  
visuals:
  - type: "bar"
    title: "Sales by Month"
    data: "Sales"
```

## License Validation

The generator will automatically validate your license key on first use.
Make sure `LICENSE_KEY.txt` contains your valid key.
