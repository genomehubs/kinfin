use anyhow::Result;
use kinfin_index::{Cluster, Index};
use kinfin_index::memmap::{save_memmap, MemmapIndex};
use std::env;
use std::fs;
use std::path::PathBuf;

#[test]
fn memmap_write_read_roundtrip() -> Result<()> {
    // build a small synthetic index
    let index = Index {
        species: vec!["A".to_string(), "B".to_string()],
        seq_names: None,
        seq_species: vec![0u32, 1u32, 0u32, 1u32],
        seq_len: vec![Some(10u32), Some(20u32), None, Some(30u32)],
        clusters: vec![
            Cluster { id: "c0".to_string(), members: vec![0u32, 1u32] },
            Cluster { id: "c1".to_string(), members: vec![2u32, 3u32] },
        ],
        meta: None,
    };

    let mut path = env::temp_dir();
    path.push(format!("kinfin_test_{}.mmap", std::process::id()));
    let path_buf: PathBuf = path.clone();

    // write memmap
    save_memmap(&index, &path_buf)?;

    // open and validate
    let mi = MemmapIndex::open(&path_buf)?;
    assert_eq!(mi.species_count(), index.species.len());
    assert_eq!(mi.seq_count(), index.seq_species.len());
    assert_eq!(mi.cluster_count(), index.clusters.len());

    // species name
    assert_eq!(mi.species_name(0)?, "A");

    // seq_species
    let seq_species = mi.seq_species_slice()?;
    assert_eq!(seq_species.len(), index.seq_species.len());
    assert_eq!(seq_species[0], 0u32);

    // seq_len raw -> None encoded as u32::MAX
    let seq_len_raw = mi.seq_len_raw_slice()?;
    assert_eq!(seq_len_raw[2], u32::MAX);

    // per-cluster checks: member counts and species-entry bytes length
    for (i, c) in index.clusters.iter().enumerate() {
        let members = mi.cluster_members_for(i)?;
        assert_eq!(members.len(), c.members.len());

        // expected number of species entries = distinct species in cluster
        let mut uniq = std::collections::HashSet::new();
        for &m in &c.members {
            uniq.insert(index.seq_species[m as usize]);
        }
        let entries_bytes = mi.cluster_species_entries_bytes_for(i)?;
        // each species entry is 32 bytes in the on-disk format
        assert_eq!(entries_bytes.len(), uniq.len() * 32);
    }

    // cleanup
    fs::remove_file(&path_buf)?;
    Ok(())
}
