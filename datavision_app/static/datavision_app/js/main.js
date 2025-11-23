document.addEventListener("DOMContentLoaded", function(){
  const file = document.getElementById("file");
  if(file){
    file.addEventListener("change", () => {
      const label = document.querySelector("label[for=\\"file\\"]");
      if(label && file.files.length) label.textContent = `Uploaded: ${file.files[0].name}`;
    });
  }
});
