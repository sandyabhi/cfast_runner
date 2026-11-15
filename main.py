from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import subprocess
import tempfile
import shutil
import uuid

app = FastAPI(title="CFAST Web Runner")

# Temporary simulation storage
RUNS_DIR = Path("/tmp/cfast-runs")
RUNS_DIR.mkdir(parents=True, exist_ok=True)


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CFAST Web Runner</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }

        h1 {
            color: #333;
        }

        .box {
            border: 1px solid #ccc;
            padding: 25px;
            border-radius: 8px;
        }

        button {
            margin-top: 15px;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }

        #result {
            margin-top: 25px;
            padding: 15px;
            white-space: pre-wrap;
            background: #f5f5f5;
            border-radius: 5px;
        }

        .success {
            border-left: 5px solid green;
        }

        .error {
            border-left: 5px solid red;
        }

        ul {
            padding-left: 20px;
        }
    </style>
</head>

<body>

    <h1>🔥 CFAST Web Runner</h1>

    <p>
        Upload a CFAST <code>.in</code> file and run the simulation.
    </p>

    <div class="box">

        <form id="uploadForm">

            <input
                type="file"
                id="file"
                name="file"
                accept=".in"
                required
            >

            <br>

            <button type="submit">
                Run CFAST Simulation
            </button>

        </form>

    </div>

    <div id="result">
        Waiting for simulation...
    </div>


<script>

document.getElementById("uploadForm").addEventListener("submit", async function(event) {

    event.preventDefault();

    const fileInput = document.getElementById("file");
    const resultDiv = document.getElementById("result");

    if (!fileInput.files.length) {
        resultDiv.innerText = "Please select a .in file.";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    resultDiv.className = "";
    resultDiv.innerText = "Running CFAST... Please wait.";

    try {

        const response = await fetch("/simulate", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.success) {

            resultDiv.className = "success";

            let output = "✅ SIMULATION SUCCESSFUL\\n\\n";

            output += "CFAST Output:\\n";
            output += data.stdout + "\\n";

            output += "\\nGenerated Files:\\n";

            data.files.forEach(file => {
                output += "• " + file + "\\n";
            });

            output += "\\nRun ID: " + data.run_id;

            resultDiv.innerText = output;

        } else {

            resultDiv.className = "error";

            resultDiv.innerText =
                "❌ SIMULATION FAILED\\n\\n" +
                "STDOUT:\\n" +
                data.stdout +
                "\\n\\nSTDERR:\\n" +
                data.stderr;
        }

    } catch (error) {

        resultDiv.className = "error";
        resultDiv.innerText = "Error: " + error;

    }

});

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "CFAST Web Runner is running"
    }


@app.post("/simulate")
async def simulate(file: UploadFile = File(...)):

    # Basic validation
    if not file.filename or not file.filename.lower().endswith(".in"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid CFAST .in file"
        )

    # Create an isolated folder for this simulation
    run_id = str(uuid.uuid4())
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    input_file = run_dir / "scenario.in"

    try:

        # Save uploaded file
        with open(input_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run CFAST
        result = subprocess.run(
            ["cfast", "scenario.in"],
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=120
        )

        # Get generated files
        files = [
            f.name
            for f in run_dir.iterdir()
            if f.is_file()
        ]

        return {
            "success": result.returncode == 0,
            "run_id": run_id,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "files": files
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "run_id": run_id,
            "stdout": "",
            "stderr": "Simulation timed out after 120 seconds",
            "files": []
        }

    except Exception as e:

        return {
            "success": False,
            "run_id": run_id,
            "stdout": "",
            "stderr": str(e),
            "files": []
        }


@app.get("/runs/{run_id}/{filename}")
def download_file(run_id: str, filename: str):

    # Prevent path traversal
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = RUNS_DIR / run_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)