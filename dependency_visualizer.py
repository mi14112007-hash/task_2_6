#!/usr/bin/env python3
import configparser
import os
import sys
import requests
import json
from collections import defaultdict
import graphviz

class DependencyVisualizer:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.params = {}
        self.graph = defaultdict(list)
        self.visited = set()
        self.cycles = []
        
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

    def build_dependency_graph(self):
        if self.params['test_mode']:
            self._test_mode_analysis()
            return
            
        package = self.params['package_name']
        version = self.params['version']
        self._bfs_with_recursion(package, version, 0)
        
        self._print_graph()
        
        if self.cycles:
            print(f"\nCyclic dependencies detected: {self.cycles}")

    def _bfs_with_recursion(self, package, version, current_depth):
        if current_depth > self.params['max_depth']:
            return
            
        if (package, version) in self.visited:
            self.cycles.append((package, version))
            return
            
        self.visited.add((package, version))
        
        filter_sub = self.params['filter_substring'].lower()
        if filter_sub and filter_sub in package.lower():
            return
            
        dependencies = self.fetch_dependencies(package, version)
        
        for dep in dependencies:
            dep_name = dep['name']
            dep_version = self._extract_version(dep['version'])
            
            self.graph[f"{package}@{version}"].append(f"{dep_name}@{dep_version}")
            
            self._bfs_with_recursion(dep_name, dep_version, current_depth + 1)

    def _extract_version(self, version_req):
        clean_version = version_req.replace('^', '').replace('~', '').replace('=', '')
        return clean_version.split(',')[0] if ',' in clean_version else clean_version

    def _test_mode_analysis(self):
        test_file = self.params['test_repo_path']
        try:
            with open(test_file, 'r') as f:
                test_data = json.load(f)
                
            print(f"\n=== Test Mode Analysis from {test_file} ===")
            for package, deps in test_data.items():
                print(f"{package} -> {deps}")
            print("===========================================")
            
        except FileNotFoundError:
            print(f"Test file {test_file} not found")
        except json.JSONDecodeError:
            print(f"Invalid JSON in test file {test_file}")

    def _print_graph(self):
        print("\n=== Dependency Graph ===")
        for package, dependencies in self.graph.items():
            if dependencies:
                print(f"{package} -> {', '.join(dependencies)}")
            else:
                print(f"{package} -> No dependencies")
        print("========================")

    def analyze_dependencies(self):
        if self.params['test_mode']:
            return
            
        load_order = self._calculate_load_order()
        self._print_load_order(load_order)
        self._compare_with_cargo(load_order)

    def _calculate_load_order(self):
        visited = set()
        load_order = []
        
        def dfs(package, version):
            node = f"{package}@{version}"
            if node in visited:
                return
                
            visited.add(node)
            
            dependencies = self.fetch_dependencies(package, version)
            
            for dep in dependencies:
                dep_name = dep['name']
                dep_version = self._extract_version(dep['version'])
                dfs(dep_name, dep_version)
                
            load_order.append(node)
            
        package = self.params['package_name']
        version = self.params['version']
        dfs(package, version)
        
        return load_order[::-1]

    def _print_load_order(self, load_order):
        print("\n=== Dependency Load Order ===")
        for i, package in enumerate(load_order, 1):
            print(f"{i}. {package}")

    def _compare_with_cargo(self, load_order):
        print("\n=== Comparison with Cargo ===")
        print("Generated load order:")
        for i, package in enumerate(load_order, 1):
            print(f"  {i}. {package}")
            
        print("\nCompare with real package manager:")
        print(f"  cargo tree --package {self.params['package_name']}")
        print("\nPossible differences:")
        print("  1. Version resolution algorithms")
        print("  2. Feature flags handling") 
        print("  3. Platform-specific dependencies")
        print("  4. Build vs normal dependencies")

    def visualize_graph(self):
        if not self.graph:
            print("No graph data to visualize")
            return
            
        graphviz_text = self._generate_graphviz_text()
        print("\n=== Graphviz Text Representation ===")
        print(graphviz_text)
        
        self._create_visualization()
        self._demonstrate_examples()
        self._compare_with_cargo_visualization()

    def _generate_graphviz_text(self):
        dot_lines = ["digraph Dependencies {"]
        dot_lines.append("  rankdir=LR;")
        dot_lines.append("  node [shape=box, style=filled, fillcolor=lightblue];")
        
        for package, dependencies in self.graph.items():
            for dep in dependencies:
                dot_lines.append(f'  "{package}" -> "{dep}";')
                
        dot_lines.append("}")
        return "\n".join(dot_lines)

    def _create_visualization(self):
        try:
            dot = graphviz.Digraph(comment='Dependency Graph')
            dot.attr(rankdir='LR')
            dot.attr('node', shape='box', style='filled', fillcolor='lightblue')
            
            for package, dependencies in self.graph.items():
                for dep in dependencies:
                    dot.edge(package, dep)
                    
            output_file = self.params['output_file']
            dot.render(output_file.replace('.png', ''), format='png', cleanup=True)
            print(f"\nGraph saved as {output_file}")
            
        except Exception as e:
            print(f"Error creating visualization: {e}")

    def _demonstrate_examples(self):
        demo_packages = [
            ("serde", "1.0.0"),
            ("tokio", "1.0.0"), 
            ("reqwest", "0.11.0")
        ]
        
        print("\n=== Visualization Examples for Three Packages ===")
        for package, version in demo_packages:
            print(f"Example visualization available for: {package} v{version}")

    def _compare_with_cargo_visualization(self):
        print("\n=== Comparison with Cargo Visualization ===")
        print("To compare with cargo visualization, run:")
        print(f"  cargo tree --package {self.params['package_name']} --graph")
        print("\nPossible differences in visualization:")
        print("  1. Different graph layout algorithms")
        print("  2. Cargo includes dev-dependencies and build-dependencies")
        print("  3. Feature-based dependency resolution")
        print("  4. Version conflict resolution strategies")

def main():
    visualizer = DependencyVisualizer()
    
    try:
        visualizer.load_config()
        visualizer.print_direct_dependencies()
        visualizer.build_dependency_graph()
        visualizer.analyze_dependencies()
        visualizer.visualize_graph()
        
        print("\n=== Analysis completed successfully! ===")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()