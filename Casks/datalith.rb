cask "datalith" do
  arch arm: "aarch64", intel: "x64"

  version "1.1.2"
  sha256 arm:   "ec2b1465b7ca1e14864ea50aa7b8329aa2fa3065920b0f76a2f04622e03d540d",
         intel: "4660bdcec0f5b59d7321cfc465ca02b97d05184ed60cad941da9447ae92562bd"

  url "https://github.com/mycelium-build/datalith-app/releases/download/v#{version}/Datalith_#{version}_#{arch}.dmg"
  name "Datalith"
  desc "Local-first knowledge workspace"
  homepage "https://datalith.work/"

  livecheck do
    url "https://updates.datalith.work/stable"
    strategy :json do |json|
      json["version"] if json["version"] != "0.0.0"
    end
  end

  auto_updates true
  depends_on :macos

  app "Datalith.app"

  uninstall quit: "build.mycelium.datalith"
end
