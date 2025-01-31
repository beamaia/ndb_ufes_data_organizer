import pandas as pd
import os
import pathlib as pl


def main():
    wrong_ids_df = pd.read_csv("wrong_ids.csv")
    patch_id = list(wrong_ids_df["patch"])

    links_made = sorted([(link.parts[-1][6:11], link) for link in pl.Path("data/ndb_ufes/link/images").iterdir()], key= lambda x: x[0])

    for patch_link, patch_path in links_made:

        if patch_link in patch_id:
            print(patch_link, "to be deleted")
            if os.path.exists(patch_path):
                os.remove(patch_path)

if __name__ == "__main__":
    main()