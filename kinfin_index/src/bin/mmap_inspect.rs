use anyhow::Result;
use kinfin_index::memmap::MemmapIndex;
use std::path::PathBuf;

fn main() -> Result<()> {
    let p = PathBuf::from("../example/index.mmap");
    let mi = MemmapIndex::open(&p)?;
    println!("species_count: {}", mi.species_count());
    println!("seq_count: {}", mi.seq_count());
    println!("cluster_count: {}", mi.cluster_count());
    println!("first species: {}", mi.species_name(0)?);
    let seq_species = mi.seq_species_slice()?;
    println!("seq_species len: {}", seq_species.len());
    let seq_len = mi.seq_len_raw_slice()?;
    println!("seq_len len: {}", seq_len.len());
    let m0 = mi.cluster_members_for(0)?;
    println!("cluster 0 members: {:?}", m0);
    // inspect species entries bytes lengths for first few clusters
    for i in 0..std::cmp::min(5, mi.cluster_count()) {
        match mi.cluster_species_entries_bytes_for(i) {
            Ok(slice) => println!("cluster {} species entries bytes len: {}", i, slice.len()),
            Err(e) => println!("cluster {} species entries error: {}", i, e),
        }
    }
    Ok(())
}
