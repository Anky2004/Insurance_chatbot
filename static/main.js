async function sendQuery() {
  const queryBox = document.getElementById("queryBox");
  const fileInput = document.getElementById("fileInput");
  const conversation = document.getElementById("conversation");

  const query = queryBox.value.trim();
  const files = fileInput.files;
  const formData = new FormData();
  formData.append("query", query);

  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  const userMsg = document.createElement("div");
  userMsg.className = "message user";
  userMsg.textContent = query || "[File uploaded]";
  conversation.appendChild(userMsg);

  const botMsg = document.createElement("div");
  botMsg.className = "message bot";
  botMsg.innerHTML = `
    <lottie-player src="https://assets3.lottiefiles.com/private_files/lf30_jzjxh7rw.json" background="transparent" speed="1" style="width: 60px; height: 60px;" loop autoplay></lottie-player>
  `;
  conversation.appendChild(botMsg);

  conversation.scrollTop = conversation.scrollHeight;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      body: formData
    });

    const message = await response.text();
    botMsg.textContent = message;
  } catch (error) {
    console.error("Error:", error);
    botMsg.textContent = "Something went wrong.";
  }

  queryBox.value = "";
  fileInput.value = "";
  conversation.scrollTop = conversation.scrollHeight;
}

// 🌗 Theme toggle
document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("themeToggle");
  toggleBtn.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    document.body.classList.toggle("light-mode");
    toggleBtn.textContent =
      document.body.classList.contains("dark-mode") ? "☀️" : "🌙";
  });
});

