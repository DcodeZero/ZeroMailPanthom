# generate_requirements.py
import platform
import sys

def generate_platform_requirements():
    with open('requirements.txt', 'r') as f:
        requirements = f.readlines()
    
    platform_reqs = []
    for req in requirements:
        # Keep requirement if it's not platform specific or matches current platform
        if 'platform_system' not in req or \
           (f'platform_system=="{platform.system()}"' in req):
            platform_reqs.append(req.split(';')[0].strip())
    
    output_file = f'requirements_{platform.system().lower()}.txt'
    with open(output_file, 'w') as f:
        f.write('\n'.join(platform_reqs))
    
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_platform_requirements()