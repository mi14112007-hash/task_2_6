#!/usr/bin/env python3
import configparser
import os
import sys
import requests
import json

class DependencyVisualizer:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.params = {}
        
    def load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file {self.config_file} not found")
            
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        expected_params = {
            'package_name': '',
            'repository_url': 'https://crates.io',
            'test_mode': 'false',
            'test_repo_path': 'test_deps.txt',
            'version': '',
            'max_depth': '3',
            'filter_substring': '',
            'output_file': 'graph.png'
        }
        
        for param, default in expected_params.items():
            try:
                value = config.get('settings', param, fallback=default)
                self.params[param] = value
            except Exception as e:
                print(f"Error reading parameter {param}: {e}")
                sys.exit(1)
                
        self.params['test_mode'] = self.params['test_mode'].lower() == 'true'
        try:
            self.params['max_depth'] = int(self.params['max_depth'])
        except ValueError:
            print("Error: max_depth must be an integer")
            sys.exit(1)
        
        print("=== Configuration Parameters ===")
        for key, value in self.params.items():
            print(f"{key}: {value}")
        print("=================================")
        
        if not self.params['package_name']:
            raise ValueError("package_name is required")
        if not self.params['version']:
            raise ValueError("version is required")

    def fetch_dependencies(self, package, version):
        url = f"https://crates.io/api/v1/crates/{package}/{version}/dependencies"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            dependencies = []
            
            for dep in data.get('dependencies', []):
                dep_info = {
                    'name': dep['crate_id'],
                    'version': dep['req'],
                    'kind': dep.get('kind', 'normal')
                }
                dependencies.append(dep_info)
                
            return dependencies
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching dependencies: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return []

    def print_direct_dependencies(self):
        package = self.params['package_name']
        version = self.params['version']
        
        print(f"Fetching dependencies for {package} v{version}...")
        
        dependencies = self.fetch_dependencies(package, version)
        
        if not dependencies:
            print("No dependencies found or error occurred")
            return
            
        print(f"\n=== Direct Dependencies for {package} v{version} ===")
        for i, dep in enumerate(dependencies, 1):
            kind = f" ({dep['kind']})" if dep['kind'] != 'normal' else ''
            print(f"{i}. {dep['name']} {dep['version']}{kind}")
        print("=============================================")

def main():
    visualizer = DependencyVisualizer()
    
    try:
        visualizer.load_config()
        visualizer.print_direct_dependencies()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()