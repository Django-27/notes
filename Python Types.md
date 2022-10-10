
```python
def func(item_a: str, item_b: int, item_c: float, item_d: bool, item_e: bytes):
    return item_a, item_b, item_c, item_d, item_d, item_e
```

 Python module typing
 - The syntax using typing is compatible with all versions, from Python 3.6 to the latest ones, including Python 3.9, Python 3.10, etc.
 - 随着Python的发展，新版本对这些类型注释提供了改进的支持，在许多情况下，甚至不需要导入和使用typing模块来声明类型注释。
 - 如果您可以为您的项目选择一个较新的Python版本，您将能够利用这种额外的简单性。请看下面的一些例子。

# List
```python
  # py36 and above
from typing import List
def process_items(items: List[str]):
    for item in items:
        print(item)
        
 # py39 and above
def process_items(items: list[str]): 
    for item in items:
        print(item)
```
# Tuple and Set
```python
  # py36 and above
from typing import Set, Tuple
def process_items(items_t: Tuple[int, int, str], items_s: Set[bytes]):
    return items_t, items_s
        
 # py39 and above
def process_items(items_t: tuple[int, int, str], items_s: set[bytes]):
    return items_t, items_s
    
```
# Dict
```python
  # py36 and above
from typing import Dict
def process_items(prices: Dict[str, float]):
    for item_name, item_price in prices.items():
        print(item_name)
        print(item_price)
        
 # py39 and above
def process_items(prices: dict[str, float]):
    for item_name, item_price in prices.items():
        print(item_name)
        print(item_price)
    
```
# Union 几种类型中的任意一个
```python
  # py36 and above
from typing import Union
def process_item(item: Union[int, str]):
    print(item)
        
 # py310 and above
def process_item(item: int | str):
    print(item)
    
```
# Possible None 也可以是None值, 也是 Union[str, None]的简化
```python
  # py36 and above include py310
from typing import Optional
def say_hi(name: Optional[str] = None):
    if name is not None:
        print(f"Hey {name}!")
    else:
        print("Hello World")
        
from typing import Union


def say_hi(name: Union[str, None] = None):
    if name is not None:
        print(f"Hey {name}!")
    else:
        print("Hello World")
        
# py310 and above 
def say_hi(name: str | None = None):
    if name is not None:
        print(f"Hey {name}!")
    else:
        print("Hello World")
    
```