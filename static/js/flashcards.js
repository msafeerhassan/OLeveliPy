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
            cardDisplay.style.display = "none";
            noCardsMsg.style.display = "block";
            noCardsMsg.textContent = "You have reviewed all due cards for now. Come back later.";
            return;
        }

        const card = cards[currentIdx];

        cardCounter.textContent = `Card ${currentIdx + 1} of ${cards.length}`;
        cardFront.textContent = card.front;
        cardBack.textContent = card.back;
        cardBack.style.display = "none";
        ratingBtns.style.display = "none";
        showAnswerBtn.style.display = "inline-block";
    }

    showAnswerBtn.addEventListener("click", function () {
        cardBack.style.display = "block";
        showAnswerBtn.style.display = "none";
        ratingBtns.style.display = "block";
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
        noCardsMsg.style.display = "block";
    } else {
        cardDisplay.style.display = "block";
        showCard();
    }
});