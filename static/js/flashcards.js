document.addEventListener("DOMContentLoaded", function () {
    const cards = window.dueCards || [];
    let currentIdx = 0;

    const noCardsMsg = document.getElementById("noCardsMsg");
    const cardDisplay = document.getElementById("cardDisplay");
    const cardCounter = document.getElementById("cardCount");
    const cardFront = document.getElementById("cardFront");
    const cardBack = document.getElementById("cardBack");
    const showAnswerBtn = document.getElementById("showAnswerBtn");
    const ratingBtns = document.getElementById("ratingBtns");

    function showCard() {
        if (currentIdx >= cards.length) {
            cardDisplay.classList.add("hidden");
            noCardsMsg.classList.remove("hidden");
            noCardsMsg.textContent = "You have reviewed all due cards for now. Come back later.";
            return;
        }

        const card = cards[currentIdx];

        cardCounter.textContent = `Card ${currentIdx + 1} of ${cards.length}`;
        cardFront.textContent = card.front;
        cardBack.textContent = card.back;
        cardBack.classList.add("hidden");
        ratingBtns.classList.add("hidden");
        showAnswerBtn.classList.remove("hidden");
    }

    showAnswerBtn.addEventListener("click", function () {
        cardBack.classList.remove("hidden");
        showAnswerBtn.classList.add("hidden");
        ratingBtns.classList.remove("hidden");
    });

    ratingBtns.addEventListener("click", async function (event) {
        const quality = event.target.getAttribute("data-quality");

        if (!quality) {
            return;
        }

        const card = cards[currentIdx];
        try {
            await fetch("/api/review-flashcard", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(
                    {
                        flashcardId: card.id,
                        quality: quality
                    }
                )
            });
        } catch (err) {
            console.log("Failed to submit review: ", err)
        }

        currentIdx++;
        showCard();
    });

    if (cards.length === 0) {
        noCardsMsg.classList.remove("hidden");
    } else {
        cardDisplay.classList.remove("hidden");
        showCard();
    }
});