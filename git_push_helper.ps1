Write-Output "Deleting index.lock if exists..."
if (Test-Path .git\index.lock) { Remove-Item .git\index.lock -Force -ErrorAction SilentlyContinue }

Write-Output "Checking status..."
git status

Write-Output "Adding files..."
git add .

Write-Output "Committing..."
git commit -m "Auto-commit: Scraper project setup"

Write-Output "Setting branch to main..."
git branch -M main

Write-Output "Configuring remote..."
# Try removing remote first to avoid error if exists
git remote remove origin 2>$null
git remote add origin https://github.com/nguyenthedai2k3-design/obito_forexfatory.git

Write-Output "Pushing to GitHub..."
git push -u origin main
