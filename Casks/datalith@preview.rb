cask "datalith@preview" do
  arch arm: "aarch64", intel: "x64"

  version "1.1.0-rc.2"
  sha256 arm:   "6b32baaf838ed42f6f1eb6f355ad609be925fe1432278ad551f8af2cb4507f84",
         intel: "38eaaf954493fde6708c560605bb47b42bbc92530c2179d8358d0cdec701da48"

  url "https://github.com/mycelium-build/datalith-app/releases/download/v#{version}/Datalith.Preview_#{version}_#{arch}.dmg"
  name "Datalith Preview"
  desc "Local-first knowledge workspace"
  homepage "https://datalith.work/"

  livecheck do
    url "https://updates.datalith.work/preview"
    strategy :json do |json|
      json["version"] if json["version"] != "0.0.0"
    end
  end

  auto_updates true
  depends_on :macos

  app "Datalith Preview.app"

  uninstall quit: "build.mycelium.datalith-preview"
end
