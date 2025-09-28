import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Temporarily patch config for testing
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

original_provider = config['llm_provider']
config['llm_provider'] = 'agent0'

# Write back temporarily
with open('config.yaml', 'w') as f:
    yaml.dump(config, f)

try:
    # Now import model
    import model
    print("Import successful")
    print(f"LLMSession is: {model.LLMSession}")
    print(f"Expected: {model.LLMAgent0Session}")
    if model.LLMSession == model.LLMAgent0Session:
        print("Provider selection works correctly")
    else:
        print("Provider selection failed")
finally:
    # Restore original config
    config['llm_provider'] = original_provider
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f)