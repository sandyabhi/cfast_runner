 
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI(title="CFAST Web Runner")


# --------------------------------------------------
# Simulation output storage
# --------------------------------------------------

# For LOCAL Docker testing, this folder will be mounted
# to an "outputs" folder on your Windows computer.
RUNS_DIR = Path("/app/outputs")
RUNS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Web page
# --------------------------------------------------

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

        li {
            margin-bottom: 8px;
        }

        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }

    </style>
</head>


<body>

    <h1>CFAST Web Runner</h1>

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

document.getElementById("uploadForm").addEventListener(
    "submit",
    async function(event) {

        event.preventDefault();

        const fileInput = document.getElementById("file");
        const resultDiv = document.getElementById("result");


        // Check file selected
        if (!fileInput.files.length) {

            resultDiv.className = "error";
            resultDiv.innerText = "Please select a .in file.";

            return;
        }


        // Create form data
        const formData = new FormData();

        formData.append(
            "file",
            fileInput.files[0]
        );


        // Show loading message
        resultDiv.className = "";

        resultDiv.innerText =
            "Running CFAST simulation... Please wait.";


        try {

            // Send file to backend
            const response = await fetch(
                "/simulate",
                {
                    method: "POST",
                    body: formData
                }
            );


            const data = await response.json();


            // --------------------------------------
            // Simulation successful
            // --------------------------------------

            if (data.success) {

                resultDiv.className = "success";


                let html = `

                    <h2>SIMULATION SUCCESSFUL</h2>

                    <h3>CFAST Output</h3>

                    <pre>${escapeHtml(data.stdout)}</pre>

                    <h3>Generated Files</h3>

                    <ul>

                `;


                data.files.forEach(file => {

                    const url =
                        "/runs/" +
                        data.run_id +
                        "/" +
                        encodeURIComponent(file);


                    html += `

                        <li>

                            <strong>${escapeHtml(file)}</strong>

                            -
                            
                            <a
                                href="${url}"
                                target="_blank"
                            >
                                View / Download
                            </a>

                        </li>

                    `;

                });


                html += `

                    </ul>

                    <p>

                        <strong>Run ID:</strong>

                        ${data.run_id}

                    </p>

                `;


                resultDiv.innerHTML = html;

            }


            // --------------------------------------
            // Simulation failed
            // --------------------------------------

            else {

                resultDiv.className = "error";

                resultDiv.innerText =

                    "SIMULATION FAILED\\n\\n" +

                    "STDOUT:\\n" +

                    data.stdout +

                    "\\n\\nSTDERR:\\n" +

                    data.stderr;

            }


        }


        // --------------------------------------
        // Request error
        // --------------------------------------

        catch (error) {

            resultDiv.className = "error";

            resultDiv.innerText =
                "Error: " + error;

        }

    }
);


// Prevent HTML injection in displayed text
function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}

</script>

</body>

</html>
"""


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():

    return HTML


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "message": "CFAST Web Runner is running"
    }


# --------------------------------------------------
# Run CFAST simulation
# --------------------------------------------------

@app.post("/simulate")
async def simulate(
    file: UploadFile = File(...)
):

    # Validate file
    if (
        not file.filename
        or not file.filename.lower().endswith(".in")
    ):

        raise HTTPException(
            status_code=400,
            detail="Please upload a valid CFAST .in file"
        )


    # Create unique simulation ID
    run_id = str(uuid.uuid4())


    # Create isolated folder
    run_dir = RUNS_DIR / run_id

    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # CFAST input filename
    input_file = run_dir / "scenario.in"


    try:

        # ------------------------------------------
        # Save uploaded file
        # ------------------------------------------

        with open(
            input_file,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        # ------------------------------------------
        # Run CFAST
        # ------------------------------------------

        result = subprocess.run(

            [
                "cfast",
                "scenario.in"
            ],

            cwd=run_dir,

            capture_output=True,

            text=True,

            timeout=120

        )


        # ------------------------------------------
        # Get generated files
        # ------------------------------------------

        files = sorted(
            [
                f.name

                for f in run_dir.iterdir()

                if f.is_file()
            ]
        )


        # ------------------------------------------
        # Return results
        # ------------------------------------------

        return {

            "success":
                result.returncode == 0,

            "run_id":
                run_id,

            "stdout":
                result.stdout,

            "stderr":
                result.stderr,

            "files":
                files

        }


    # ----------------------------------------------
    # Simulation timeout
    # ----------------------------------------------

    except subprocess.TimeoutExpired:

        return {

            "success":
                False,

            "run_id":
                run_id,

            "stdout":
                "",

            "stderr":
                "Simulation timed out after 120 seconds",

            "files":
                []

        }


    # ----------------------------------------------
    # Other errors
    # ----------------------------------------------

    except Exception as e:

        return {

            "success":
                False,

            "run_id":
                run_id,

            "stdout":
                "",

            "stderr":
                str(e),

            "files":
                []

        }


    finally:

        await file.close()


# --------------------------------------------------
# View / download generated files
# --------------------------------------------------

@app.get("/runs/{run_id}/{filename}")
def download_file(
    run_id: str,
    filename: str
):

    # Prevent path traversal
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )


    # Prevent invalid run IDs
    if (
        "/" in run_id
        or "\\" in run_id
        or ".." in run_id
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid run ID"
        )


    file_path = (
        RUNS_DIR
        / run_id
        / filename
    )


    # Check file exists
    if not file_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )


    # Return the file
    return FileResponse(
        path=file_path,
        filename=filename
    )