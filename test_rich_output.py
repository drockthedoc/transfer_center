from rich.console import Console
from rich.panel import Panel

console = Console()
console.print(Panel("Hello from Rich in Python!", title="[bold green]Test Output[/bold green]", border_style="green"))
console.print("If you see this, Rich is working in your Python environment.")
