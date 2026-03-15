import finshare as fs
import inspect

def main():
    with open('api_results.txt', 'w', encoding='utf-8') as f:
        functions = [name for name, obj in inspect.getmembers(fs) if inspect.isfunction(obj) or inspect.isbuiltin(obj) or type(obj).__name__ == 'function']
        f.write("--- finshare functions ---\n")
        f.write('\n'.join(functions) + '\n\n')
        
        try:
            f.write(f"--- get_historical_data signature ---\n")
            f.write(str(inspect.signature(fs.get_historical_data)) + '\n')
            f.write(str(fs.get_historical_data.__doc__) + '\n\n')
        except Exception as e:
            f.write(str(e) + '\n\n')
            
        try:
            for n in functions:
                if 'adj' in n.lower() or 'factor' in n.lower():
                    f.write(f"--- {n} signature ---\n")
                    f.write(str(inspect.signature(getattr(fs, n))) + '\n')
                    f.write(str(getattr(fs, n).__doc__) + '\n\n')
        except Exception as e:
            f.write(str(e) + '\n\n')

if __name__ == "__main__":
    main()
