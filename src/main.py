import json
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich import (
    print as rprint,
)  # Use rprint to avoid conflict with built-in print if needed
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from src.core.decision import recommend_campus
from src.core.models import (
    HospitalCampus,
    Location,
    PatientData,
    TransferRequest,
    TransportMode,
    WeatherData,
)
from src.llm.classification import parse_patient_text

app = typer.Typer(help="Transfer Recommendation CLI Tool")


@app.command(name="recommend")
def recommend_transfer(
    ctx: typer.Context,
    hospitals_file: Path = typer.Option(
        "data/sample_hospital_campuses.json",
        "--hospitals",
        "-h",
        help="Path to hospital data JSON file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    weather_file: Path = typer.Option(
        "data/sample_weather_conditions.json",
        "--weather",
        "-w",
        help="Path to weather data JSON file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    patient_notes_file: Optional[Path] = typer.Option(
        None,
        "--notes-file",
        "-nf",
        help="Path to unstructured patient notes text file.",
        exists=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
    ),
    patient_data_file: Optional[Path] = typer.Option(
        None,
        "--patient-file",
        "-pf",
        help="Path to structured patient data JSON file (uses first patient in list).",
        exists=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
    ),
    patient_id: str = typer.Option("PAT_CLI_001", "--pid", help="Patient ID."),
    chief_complaint: Optional[str] = typer.Option(
        None,
        "--complaint",
        help="Patient's chief complaint (if not using files or to override notes).",
    ),
    clinical_history: Optional[str] = typer.Option(
        None,
        "--history",
        help="Patient's clinical history (if not using files or to override notes).",
    ),
    sending_facility_name: str = typer.Option(
        "Sending General CLI", "--sfn", help="Name of the sending facility."
    ),
    sending_lat: float = typer.Option(
        29.7300, "--slat", help="Latitude of sending facility."
    ),
    sending_lon: float = typer.Option(
        -95.3800, "--slon", help="Longitude of sending facility."
    ),
    transport_modes_csv: str = typer.Option(
        "GROUND_AMBULANCE,AIR_AMBULANCE",
        "--transport",
        help="Comma-separated list of available transport modes (e.g., GROUND_AMBULANCE,AIR_AMBULANCE).",
    ),
):
    """
    Recommends a hospital campus for patient transfer based on various inputs.
    """
    console = Console()
    rprint(
        f"[bold cyan]Starting recommendation process for patient: {patient_id}[/bold cyan]"
    )

    # 1. Load Data
    try:
        with open(hospitals_file, "r") as f:
            hospitals_data = json.load(f)
            all_hospital_campuses = [HospitalCampus(**data) for data in hospitals_data]
        rprint(
            f":hospital: Loaded {
                len(all_hospital_campuses)} hospital campuses from [italic]{hospitals_file}[/italic]"
        )

        with open(weather_file, "r") as f:
            weather_data_list = json.load(f)
            # Use the first weather condition for simplicity in this CLI
            current_weather_condition = WeatherData(**weather_data_list[0])
        rprint(
            f":sun_behind_cloud: Loaded weather data (using first entry) from [italic]{weather_file}[/italic]"
        )
    except Exception as e:
        rprint(f"[bold red]:x: Error loading data files: {e}[/bold red]")
        raise typer.Exit(code=1)

    # 2. Prepare PatientData
    patient_data_obj: Optional[PatientData] = None
    llm_derived_complaint = "Not processed by LLM."
    llm_derived_history = "Not processed by LLM."
    llm_vitals: Dict[str, str] = {}

    sending_facility_location = Location(latitude=sending_lat, longitude=sending_lon)

    if patient_notes_file:
        rprint(
            f":page_facing_up: Processing patient notes from [italic]{patient_notes_file}[/italic]..."
        )
        try:
            notes_content = patient_notes_file.read_text()
            llm_output = parse_patient_text(notes_content)

            # Prioritize CLI input for complaint/history if provided, else use LLM
            # summary
            final_complaint = (
                chief_complaint
                if chief_complaint
                else llm_output.get(
                    "raw_text_summary", "Summary unavailable from notes."
                )
            )
            # For history, LLM output doesn't explicitly provide a structured history.
            # We'll use the CLI history if provided, or a placeholder.
            final_history = (
                clinical_history
                if clinical_history
                else "Clinical history not detailed in notes summary or CLI."
            )

            llm_derived_complaint = llm_output.get(
                "raw_text_summary", "Summary unavailable."
            )
            llm_vitals = llm_output.get("extracted_vital_signs", {})

            patient_data_obj = PatientData(
                patient_id=patient_id,
                chief_complaint=final_complaint,
                clinical_history=final_history,
                vital_signs=llm_vitals,  # Use LLM extracted vitals if available
                labs={},  # Labs usually not in initial notes
                current_location=sending_facility_location,  # Assume patient is at sending facility
            )
            rprint(
                f"  [green]:heavy_check_mark: Patient data constructed from notes file. LLM summary for complaint: '{llm_derived_complaint}'[/green]"
            )
            if chief_complaint:
                rprint(
                    f"  [yellow]:information_source: Used CLI override for chief complaint.[/yellow]"
                )
            if clinical_history:
                rprint(
                    f"  [yellow]:information_source: Used CLI override for clinical history.[/yellow]"
                )

        except Exception as e:
            rprint(f"[bold red]:x: Error processing patient notes file: {e}[/bold red]")
            raise typer.Exit(code=1)

    elif patient_data_file:
        rprint(
            f":page_facing_up: Loading patient data from [italic]{patient_data_file}[/italic]..."
        )
        try:
            with open(patient_data_file, "r") as f:
                structured_patient_list = json.load(f)
                if not structured_patient_list:
                    rprint(f"[bold red]:x: Patient data file is empty.[/bold red]")
                    raise typer.Exit(code=1)
                # Use first patient in the list
                patient_data_dict = structured_patient_list[0]
                patient_data_obj = PatientData(**patient_data_dict)
            rprint(
                f"  [green]:heavy_check_mark: Patient data loaded from structured file for ID: {
                    patient_data_obj.patient_id}[/green]"
            )
        except Exception as e:
            rprint(
                f"[bold red]:x: Error loading structured patient data file: {e}[/bold red]"
            )
            raise typer.Exit(code=1)

    else:  # Direct CLI input for patient info (or defaults)
        rprint(":keyboard: Using direct CLI inputs for patient data...")
        if not chief_complaint or not clinical_history:
            rprint(
                "[bold yellow]:warning: Chief complaint or clinical history not provided directly via CLI. Using placeholders or defaults. Consider using --notes-file or --patient-file for more complete data.[/bold yellow]"
            )

        patient_data_obj = PatientData(
            patient_id=patient_id,
            chief_complaint=(
                chief_complaint if chief_complaint else "Not specified via CLI."
            ),
            clinical_history=(
                clinical_history if clinical_history else "Not specified via CLI."
            ),
            vital_signs={},  # No direct CLI input for these in this example
            labs={},
            current_location=sending_facility_location,
        )
        rprint(
            f"  [green]:heavy_check_mark: Patient data constructed from CLI arguments.[/green]"
        )

    if (
        not patient_data_obj
    ):  # Should not happen if logic is correct, but as a safeguard
        rprint("[bold red]:x: Failed to prepare patient data. Exiting.[/bold red]")
        raise typer.Exit(code=1)

    # 3. Parse Transport Modes
    parsed_transport_modes: List[TransportMode] = []
    if transport_modes_csv:
        modes_str = transport_modes_csv.split(",")
        for mode_str in modes_str:
            try:
                parsed_transport_modes.append(TransportMode[mode_str.strip().upper()])
            except KeyError:
                rprint(
                    f"[bold yellow]:warning: Invalid transport mode '{
                        mode_str.strip()}' provided. Ignoring.[/bold yellow]"
                )
    if not parsed_transport_modes:  # Default if none valid or provided
        parsed_transport_modes = [TransportMode.GROUND_AMBULANCE]  # Default to ground
        rprint(
            f"[yellow]:information_source: No valid transport modes provided or parsed. Defaulting to: {parsed_transport_modes}[/yellow]"
        )
    rprint(
        f":ambulance::helicopter: Using available transport modes: {
            [
                mode.value for mode in parsed_transport_modes]}"
    )

    # 4. Construct TransferRequest
    transfer_request = TransferRequest(
        request_id="REQ_" + patient_data_obj.patient_id,  # Simple request ID
        patient_data=patient_data_obj,
        sending_facility_name=sending_facility_name,
        sending_facility_location=sending_facility_location,
        preferred_transport_mode=None,  # Decision engine will determine best mode
    )
    rprint(
        f":clipboard: Transfer request created with ID: {transfer_request.request_id}"
    )

    # 5. Call recommend_campus
    rprint("\n[bold blue]Calling Decision Engine...[/bold blue]")
    recommendation = recommend_campus(
        request=transfer_request,
        campuses=all_hospital_campuses,
        current_weather=current_weather_condition,
        available_transport_modes=parsed_transport_modes,
    )

    # 6. Print Results
    rprint("\n[bold magenta]----- Recommendation Result ----- [/bold magenta]")
    if recommendation:
        console.print(
            f"[bold green]Recommendation for Request ID: {
                recommendation.transfer_request_id}[/bold green]"
        )

        table = Table(
            title="Recommendation Details", show_header=True, header_style="bold blue"
        )
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Value", style="magenta")

        recommended_campus_name = "N/A"
        for campus_obj in all_hospital_campuses:
            if campus_obj.campus_id == recommendation.recommended_campus_id:
                recommended_campus_name = campus_obj.name
                break

        table.add_row(
            "Recommended Campus",
            f"{recommended_campus_name} (ID: {recommendation.recommended_campus_id})",
        )
        table.add_row("Reason", recommendation.reason)
        table.add_row(
            "Confidence Score",
            (
                f"{recommendation.confidence_score:.2f}"
                if recommendation.confidence_score is not None
                else "N/A"
            ),
        )

        console.print(table)

        if recommendation.explainability_details:
            console.print("\n[bold]Explainability Details:[/bold]")
            console.print(
                JSON(json.dumps(recommendation.explainability_details, indent=2))
            )

        if recommendation.notes:
            console.print("\n[bold]Full Decision Notes Log:[/bold]")
            for note in recommendation.notes:
                console.print(f"- {note}")
    else:
        console.print(
            "[bold red]:x: No suitable campus found for the given criteria.[/bold red]"
        )


if __name__ == "__main__":
    app()
