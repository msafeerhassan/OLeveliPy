document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("pastPaperExaminerForm");
    const progressStatus = document.getElementById("progressStatus");
    const resultsContainer = document.getElementById("allQuestionsResults");

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    function renderSpecificResult(result, historyEntryId) {
        let breakDownHtml = "";
        (result.breakdown || []).forEach(function (point) {
            breakDownHtml += `<li>[${escapeHtml(point.status)}] ${escapeHtml(point.point)} - ${escapeHtml(point.reasoning)}</li>`;
        });

        let mismatchHtml = "";
        if (result.question_number_mismatch_warning) {
            mismatchHtml = `<p style="color: orange;"><strong>${escapeHtml(result.question_number_mismatch_warning)}</strong></p>`;
        }

        let coachLinkHtml = "";
        if (historyEntryId) {
            coachLinkHtml = `<p><a href="/coach-chat?about=${encodeURIComponent(historyEntryId)}">Ask my coach about this</a></p>`;
        }

        resultsContainer.innerHTML = `
            <div>
                <h2>Question ${escapeHtml(result.question_number_requested)} <span class="markedScore">${escapeHtml(result.marks_awarded)}/${escapeHtml(result.marks_total)}</span></h2>
                ${mismatchHtml}
                <p><strong>Transcription:</strong> ${escapeHtml(result.transcription)}</p>
                <ul>${breakDownHtml}</ul>
                <p><strong>Feedback:</strong> ${escapeHtml(result.overall_feedback)}</p>
                ${coachLinkHtml}
            </div>
        `;
    }

    form.addEventListener("submit", async function (event) {

        event.preventDefault();

        const questionScope = form.querySelector('input[name="questionScope"]:checked').value;

        progressStatus.textContent = questionScope === "specific" ? "Grading your answer..." : "Uploading Images and Identifying Questions...";
        resultsContainer.innerHTML = "";

        const formData = new FormData(form);

        let submitResponse;

        try {
            submitResponse = await fetch("/past-paper-checker/submit", {
                method: "POST",
                body: formData
            });
        } catch (err) {
            progressStatus.textContent = "Failed to Submit: " + err;
            return;
        }

        const rawResponseText = await submitResponse.text();

        let submitData;

        try {
            submitData = JSON.parse(rawResponseText)
        } catch (err) {
            console.log("RAW SERVER RESPONSE:", rawResponseText)
            progressStatus.textContent = `Failed to parse server response (status ${submitResponse.status}): ${err}`;
            return;
        }

        if (!submitData.status) {
            progressStatus.textContent = "Failed: " + submitData.result;
            return;
        }

        if (submitData.mode === "specific") {
            renderSpecificResult(submitData.result, submitData.historyEntryId);
            progressStatus.textContent = "Done!";
            return ;
        }

        const segments = submitData.segments;
        const imagePaths = submitData.imagePaths;

        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            progressStatus.textContent = `Grading Question ${segment.question_number} (${i + 1} of ${segments.length})...`;

            const segmentImagePaths = segment.image_indices.map(function (index) {
                return imagePaths[index];
            });

            let gradeResponse;

            try {
                gradeResponse = await fetch("/api/grade-question", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        subjectName: submitData.subjectName,
                        subjectCode: submitData.subjectCode,
                        examinationYear: submitData.examinationYear,
                        examinationSeries: submitData.examinationSeries,
                        variant: submitData.variant,
                        questionNumber: segment.question_number,
                        markSchemePath: submitData.markSchemePath,
                        answerImagesPath: segmentImagePaths
                    })
                });
            } catch (err) {
                resultsContainer.innerHTML += `<p class="errorText">Question ${escapeHtml(segment.question_number)}: request failed (${escapeHtml(err)})</p>`;
                continue;
            }

            const gradeData = await gradeResponse.json();

            if (!gradeData.status) {
                resultsContainer.innerHTML += `<p class="errorText">Question ${escapeHtml(segment.question_number)}: grading failed (${escapeHtml(gradeData.result)})</p>`;
                continue;
            }

            const result = gradeData.result;

            resultsContainer.innerHTML += `
            <div>
                <h3>Question ${escapeHtml(segment.question_number)} <span class="markedScore">${escapeHtml(result.marks_awarded)}/${escapeHtml(result.marks_total)}</span></h3>
                <p>${escapeHtml(result.overall_feedback)}</p>
            </div>
            `;
        }

        progressStatus.textContent = "Done!";
    });
});