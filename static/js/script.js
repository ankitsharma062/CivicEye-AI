console.log("Current URL:", window.location.href);

let model;
let maxPredictions;

let aiDetectedIssue = "";
let aiConfidence = 0;

let verificationStatus = "";

// Image Upload

const imageUpload =
    document.getElementById("imageUpload");

    if (!imageUpload) {
    console.log(
        "Report page elements not found"
    );
}
else {

const previewImage =
    document.getElementById("previewImage");

const previewContainer =
    document.getElementById("previewContainer");

const removeImage =
    document.getElementById("removeImage");


// Show Preview

imageUpload.addEventListener("change", function () {

    const file = this.files[0];

    if (!file) return;

    if (file.type.startsWith("image")) {

        const reader = new FileReader();

        reader.onload = function (e) {

            previewImage.src = e.target.result;

            previewContainer.style.display = "block";

            previewImage.onload = function () {

                predictImage();

            };

        };

        reader.readAsDataURL(file);
    }
});


// Remove Preview

removeImage.addEventListener("click", function () {

    imageUpload.value = "";

    previewImage.src = "";

    previewContainer.style.display = "none";

});


// GPS Location

const gpsBtn =
    document.getElementById("gpsBtn");

const locationInput =
    document.getElementById("location");

gpsBtn.addEventListener("click", function () {

    console.log("GPS button clicked");

    if (!navigator.geolocation) {

        alert("Geolocation is not supported by this browser.");

        return;
    }

    navigator.geolocation.getCurrentPosition(

        function (position) {

            console.log("Location received");

            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;

            locationInput.value =
                latitude + "," + longitude;

            console.log(
                "Coordinates:",
                latitude,
                longitude
            );

        },

        function (error) {

            console.log(
                "GPS Error Code:",
                error.code
            );

            console.log(
                "GPS Error Message:",
                error.message
            );

            if (error.code === 1) {

    alert(
        "Location permission denied. Please allow location access in Chrome."
    );

}

            else if (error.code === 2) {

                alert(
                    "Location unavailable. Please check GPS or internet connection."
                );

            }

            else if (error.code === 3) {

                alert(
                    "Location request timed out. Please try again."
                );

            }

        },

        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }

    );

});


// THIS CHARACTER COUNTER CODE HERE

const description =
    document.getElementById("description");

const charCount =
    document.getElementById("charCount");

description.addEventListener("input", function () {

    // Limit to 300 characters
    if (this.value.length > 300) {
        this.value = this.value.substring(0, 300);
    }

    const currentLength = this.value.length;

    charCount.textContent =
        `${currentLength} / 300 characters`;

    // Color changes
    if (currentLength <= 200) {
        charCount.style.color = "green";
    }
    else if (currentLength <= 280) {
        charCount.style.color = "orange";
    }
    else {
        charCount.style.color = "red";
    }

});


// Complaint ID + Validation

const submitBtn =
    document.getElementById("submitBtn");

const successMessage =
    document.getElementById("successMessage");

submitBtn.addEventListener("click", function () {

    const issue =
        document.getElementById("issueCategory").value;

    const location =
        document.getElementById("location").value;

    const descriptionText =
        document.getElementById("description").value;


    if (

        aiDetectedIssue !== "" &&

        aiDetectedIssue !==
        "No Issue Detected" &&

        issue !== aiDetectedIssue

    ) {

        const useAISuggestion =
            confirm(

                "⚠ Category Mismatch Detected\n\n" +

                "AI detected: " +
                aiDetectedIssue +

                "\n\nYou selected: " +
                issue +

                "\n\nPress OK to use AI suggestion.\n" +

                "Press Cancel to keep your selection."

            );

        if (useAISuggestion) {

            document.getElementById(
                "issueCategory"
            ).value =
                aiDetectedIssue;

        }

    }

    if (
        issue === "Select Issue" ||
        location.trim() === "" ||
        descriptionText.trim() === ""
    ) {

        alert("Please complete all required fields.");

        return;
    }

    let complaintID =
    "CIV" + Date.now();

const reportData = {

    complaintID: complaintID,

    issue: issue,

    location: location,

    description: descriptionText,

    status: "Pending",

    date: new Date().toLocaleDateString()

};

    // Save to localStorage (temporary)

let reports =
    JSON.parse(localStorage.getItem("reports")) || [];

reports.push(reportData);

localStorage.setItem(
    "reports",
    JSON.stringify(reports)
);


// Save to SQLite through Flask

const formData = new FormData();

formData.append(
    "complaint_id",
    complaintID
);

formData.append(
    "issue",
    issue
);

formData.append(
    "user_category",
    issue
);

formData.append(
    "ai_prediction",
    aiDetectedIssue
);

formData.append(
    "ai_confidence",
    aiConfidence
);

formData.append(
    "verification_status",
    verificationStatus
);

formData.append(
    "location",
    location
);

formData.append(
    "description",
    descriptionText
);

formData.append(
    "status",
    "Pending"
);

formData.append(
    "date",
    new Date().toLocaleDateString()
);

const imageFile =
    document.getElementById(
        "imageUpload"
    ).files[0];

if (imageFile) {

    formData.append(
        "image",
        imageFile
    );

}

console.log("FORM DATA CONTENTS:");

for (let pair of formData.entries()) {

    console.log(pair[0], pair[1]);

}

fetch("/save_report", {

    method: "POST",

    body: formData

})
.then(response => response.json())
.then(data => {

    console.log(
        "Database Save:",
        data.message
    );

})
.catch(error => {

    console.error(
        "Database Error:",
        error
    );

});

    successMessage.innerHTML =
        `
    <div style="
        margin-top:15px;
        padding:15px;
        border-radius:10px;
        background:#e8f5e9;">

        <h3>✅ Report Submitted Successfully</h3>

        <p>
            Complaint ID:
            <strong>${complaintID}</strong>
        </p>

    </div>
    `;


});

async function loadModel() {

    const modelURL =
    "/static/model/model.json";

const metadataURL =
    "/static/model/metadata.json";

    model =
        await tmImage.load(
            modelURL,
            metadataURL
        );

    maxPredictions =
        model.getTotalClasses();

    console.log(
        "AI Model Loaded Successfully"
    );
}

loadModel();

async function predictImage() {

    const prediction =
        await model.predict(previewImage);

    let highestPrediction =
        prediction[0];

    for (
        let i = 1;
        i < prediction.length;
        i++
    ) {

        if (
            prediction[i].probability >
            highestPrediction.probability
        ) {

            highestPrediction =
                prediction[i];
        }
    }

    const confidence =
        (
            highestPrediction.probability * 100
        ).toFixed(1);

        aiConfidence = confidence;


    let displayName =
        highestPrediction.className;

    if (
        highestPrediction.className ===
        "garbage"
    ) {

        displayName =
            "Garbage Dump";

    }

    else if (
        highestPrediction.className ===
        "pothole"
    ) {

        displayName =
            "Pothole";

    }

    else if (
        highestPrediction.className ===
        "drainoverflow"
    ) {

        displayName =
            "Drainage Overflow";

    }

    else if (
        highestPrediction.className ===
        "cleanroad"
    ) {

        displayName =
            "No Issue Detected";

    }

    aiDetectedIssue =
        displayName;

    console.log(
        "AI Stored:",
        aiDetectedIssue
    );

    let status = "";

    if (confidence >= 80) {

    status =
        "✅ High Confidence";

    verificationStatus =
        "AI Verified";

}

else if (confidence >= 60) {

    status =
        "⚠ Moderate Confidence";

    verificationStatus =
        "Human Review Needed";

}

else {

    status =
        "⚠ Please Verify Before Submitting";

    verificationStatus =
        "Admin Verification Required";

}

    let results =
        `
<h3>🤖 AI Verification</h3>

<p>
<b>Detected Issue:</b>
${displayName}
</p>

<p>
<b>Confidence:</b>
${confidence}%
</p>

<p>
<b>Status:</b>
${status}
</p>
`;

    document.getElementById(
        "predictionResult"
    ).innerHTML = results;

    console.log(
        "Highest Prediction:",
        highestPrediction.className
    );

    const issueCategory =
        document.getElementById("issueCategory");

    const predictedClass =
        highestPrediction.className.toLowerCase();

    if (predictedClass === "garbage") {

        issueCategory.value =
            "Garbage Dump";

    }

    else if (predictedClass === "pothole") {

        issueCategory.value =
            "Pothole";

    }

    else if (predictedClass === "drainoverflow") {

        issueCategory.value =
            "Drainage Overflow";

    }

    else if (predictedClass === "cleanroad") {

        alert(
            "AI did not detect any civic issue in this image."
        );

    }
}
}
