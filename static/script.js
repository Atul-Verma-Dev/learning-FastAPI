document.querySelector("#btn").addEventListener("click", () => {

    fetch("/api/message")
        .then(response => response.json())
        .then(data => {
            document.querySelector("#result").innerHTML = data.message;
        });

});