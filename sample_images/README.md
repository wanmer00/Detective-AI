# Demo samples — provenance

These images are shown in the Scanner's "Demo samples" panel. They run through exactly the same
analysis pipeline as user uploads; no expected result is hard-coded anywhere.

| Demo ID | File | Label | Source | License |
|---|---|---|---|---|
| edited-camera | real_landscape_hopetoun_falls.jpg | Camera photo, later edited (timeline showcase) | [Commons: Hopetoun falls](https://commons.wikimedia.org/wiki/File:Hopetoun_falls.jpg), Diliff, Canon EOS 10D; metadata shows a 2005 capture (UTC+10) and a 2009 Photoshop CS4 save (UTC+01) | CC BY-SA 3.0 |
| real-people | real_people_broadstairs_folk_week.jpg | Genuine photo | [Commons: Broadstairs Folk Week](https://commons.wikimedia.org/wiki/File:Broadstairs_Folk_Week_Pavilion_Gardens_conversation,_Broadstairs,_Kent,_England_01.jpg), "Quality images of people" (1280px thumbnail) | CC BY-SA 4.0 |
| real-portrait | real_portrait_armstrong.jpg | Genuine photo (face) | [Commons: Neil Armstrong pose](https://commons.wikimedia.org/wiki/File:Neil_Armstrong_pose.jpg), NASA 1969 | Public domain |
| ai-zvd | ai_stable_diffusion_zvd.png | AI-generated | [Commons: 2023-03 AI images ZvD 01](https://commons.wikimedia.org/wiki/File:2023-03_AI_images_ZvD_01.png), Stable Diffusion, by Ziko (1280px thumbnail) | Public domain |
| ai-mountains | ai_artwork_mountains.jpg | AI-generated | [Commons: AI Artwork of Mountains](https://commons.wikimedia.org/wiki/File:AI_Artwork_of_Mountains.jpg), by David J | Public domain |

## Files kept but not in the demo list

These were removed from the demo because the current detector (SwinV2) classifies them wrongly. They
are kept to document that limitation:

- Note on `real_landscape_hopetoun_falls.jpg` (now back in the demo as `edited-camera`): SwinV2 alone gives it 0.99
  "AI" (a false positive), but multi-view scoring marks the detector unreliable on it, and the verdict comes from the
  camera EXIF + Photoshop history + consistent timeline: "Potential manipulation / editing".
- `ai_stable_diffusion_comet.jpg`: Stable Diffusion image by Prototyperspective,
  [Commons](https://commons.wikimedia.org/wiki/File:A_colonized_comet_with_a_long_abandoned_reception_center_above_underground_facility_(AI_art).jpg), CC0.
  SwinV2: 0.035 at full 3072px resolution (missed), but 0.9999 on the 1280px Commons thumbnail. The detector is resolution-sensitive.
- `manipulated_copymove_hopetoun.jpg`: copy-move forgery made from the Hopetoun photo with
  `backend/scripts/make_manipulated_sample.py`. Detective AI has no splicing/copy-move detector; it reports
  this image as "Likely AI" because the source photo is already a false positive.
