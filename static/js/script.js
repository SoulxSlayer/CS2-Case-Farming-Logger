document.addEventListener('DOMContentLoaded', function() {

    // --- Edit Modal Logic ---
    const editModal = document.getElementById('editProgressModal');
    if (editModal) {
        const editForm = document.getElementById('editProgressForm');
        const editAccountNameSpan = document.getElementById('editAccountName');
        const editWeekStartSpan = document.getElementById('editWeekStart');
        const editDropFarmedCheck = document.getElementById('edit_drop_farmed');
        const editCaseNameSelect = document.getElementById('edit_case_name');
        const editAdditionalDropInput = document.getElementById('edit_additional_drop');
        // const editProgressIdInput = document.getElementById('edit_progress_id'); // If using hidden input

        editModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;

            // Extract info from data-* attributes
            const progressId = button.getAttribute('data-progress-id');
            const accountName = button.getAttribute('data-account-name');
            const weekStart = button.getAttribute('data-week-start');
            const dropFarmed = button.getAttribute('data-drop-farmed') === 'true';
            const caseName = button.getAttribute('data-case-name');
            const additionalDrop = button.getAttribute('data-additional-drop');

            // Update the modal's content
            editForm.action = `/update_progress/${progressId}`; // Set the form action URL
            editAccountNameSpan.textContent = accountName;
            editWeekStartSpan.textContent = weekStart;
            editDropFarmedCheck.checked = dropFarmed;
            editCaseNameSelect.value = caseName || ""; // Set selected option, handle null/empty
            editAdditionalDropInput.value = additionalDrop || ""; // Set value, handle null/empty
            // editProgressIdInput.value = progressId; // If using hidden input
        });
    }

    // --- Other Weeks Fetch Logic ---
    const fetchButton = document.getElementById('fetch-other-week');
    const otherWeekDateInput = document.getElementById('other_week_date');
    const otherWeekTbody = document.getElementById('other-week-tbody');
    const otherWeekError = document.getElementById('other-week-error');

    if (fetchButton && otherWeekDateInput && otherWeekTbody && otherWeekError) {
        fetchButton.addEventListener('click', function() {
            const selectedDate = otherWeekDateInput.value;
            if (!selectedDate) {
                showError('Please select a date first.');
                return;
            }

            // Optional: Check if the selected date is a Wednesday?
            const dateObj = new Date(selectedDate + 'T00:00:00Z'); // Treat as UTC
             // getUTCDay(): Sunday is 0, Wednesday is 3
            if (dateObj.getUTCDay() !== 3) {
                showError('Please select a Wednesday.');
                // Optionally clear the input or revert
                // otherWeekDateInput.value = ''; // Clear if invalid
                return;
            }


            hideError(); // Hide previous errors
            otherWeekTbody.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>'; // Show loading state

            fetch(`/get_week_data?date=${selectedDate}`)
                .then(response => {
                    if (!response.ok) {
                        // Try to parse error json from backend if possible
                         return response.json().then(err => { throw new Error(err.error || `HTTP error! Status: ${response.status}`) });
                    }
                    return response.json();
                })
                .then(data => {
                    otherWeekTbody.innerHTML = ''; // Clear loading/previous data
                    if (data.length === 0) {
                        otherWeekTbody.innerHTML = '<tr><td colspan="4" class="text-center">No progress found for this week.</td></tr>';
                    } else {
                        data.forEach(entry => {
                            const row = otherWeekTbody.insertRow();
                            const farmedText = entry.drop_farmed ? 'Yes' : 'No';
                            const caseNameText = entry.case_name || 'N/A';
                            const additionalDropText = entry.additional_drop || '-';
                            const accountLink = `<a href="https://steamcommunity.com/profiles/${entry.steamid}" target="_blank">${entry.account_name}</a>`;

                            row.innerHTML = `
                                <td>${accountLink}</td>
                                <td>${farmedText}</td>
                                <td>${caseNameText}</td>
                                <td>${additionalDropText}</td>
                            `;
                        });
                    }
                })
                .catch(error => {
                    console.error('Error fetching other week data:', error);
                    showError(`Failed to fetch data: ${error.message}`);
                     otherWeekTbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading data.</td></tr>';
                });
        });
    }

    function showError(message) {
         if (otherWeekError) {
            otherWeekError.textContent = message;
            otherWeekError.classList.remove('d-none');
         }
    }
    function hideError() {
         if (otherWeekError) {
             otherWeekError.classList.add('d-none');
         }
    }

});